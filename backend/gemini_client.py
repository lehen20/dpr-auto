import google.generativeai as genai
import httpx
import logging
import time
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import asyncio
import aiofiles
from config import Settings
from exceptions import GeminiAPIException, FileUploadException

logger = logging.getLogger(__name__)


class GeminiFileSearchClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        genai.configure(api_key=settings.google_api_key)
        self.api_key = settings.google_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._file_search_store = None
    
    async def initialize_file_search_store(self) -> str:
        try:
            if not self._file_search_store:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/fileSearchStores",
                        headers={"Content-Type": "application/json"},
                        params={"key": self.api_key},
                        json={"displayName": "Document Search Store"}
                    )
                    response.raise_for_status()
                    self._file_search_store = response.json()
                    logger.info(f"Created file search store: {self._file_search_store['name']}")
            return self._file_search_store['name']
        except Exception as e:
            logger.error(f"Failed to initialize file search store: {e}")
            raise
    
    async def upload_file(self, file_path: str, filename: str) -> str:
        try:
            store_name = await self.initialize_file_search_store()
            
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                file_content = await f.read()
            
            async with httpx.AsyncClient(timeout=300) as client:
                # Create multipart form data
                files = {'file': (filename, file_content)}
                data = {'displayName': filename}
                
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/upload/v1beta/{store_name}:uploadToFileSearchStore",
                    params={"key": self.api_key},
                    files=files,
                    data=data
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Upload failed with status {response.status_code}: {error_text}")
                    raise GeminiAPIException(f"Upload failed: {error_text}")
                
                operation = response.json()
            
            # Wait for operation to complete
            operation_name = operation.get('name', '')
            while not operation.get('done', False):
                await asyncio.sleep(2)
                async with httpx.AsyncClient() as client:
                    op_response = await client.get(
                        f"{self.base_url}/{operation_name}",
                        params={"key": self.api_key}
                    )
                    op_response.raise_for_status()
                    operation = op_response.json()
            
            logger.info(f"Uploaded file {filename} to store {store_name}")
            return operation_name
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise
    
    async def search_and_generate(self, query: str, store_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not store_name:
                store_name = await self.initialize_file_search_store()

            url = f"{self.base_url}/models/{self.settings.gemini_model}:generateContent"
            params = {"key": self.api_key}

            body = {
                "contents": [
                    {
                        # contents -> parts -> text (exact shape required)
                        "parts": [
                            {"text": f"Based on the uploaded documents, please answer: {query}\n\n"
                                    "Provide a comprehensive answer with relevant citations from the documents."}
                        ]
                    }
                ],
                # tools must be top-level for REST calls
                "tools": [
                    {
                        "file_search": {
                            "file_search_store_names": [store_name]
                        }
                    }
                ],
                # optional top-level fields you may add:
                # "temperature": 0.0,
                # "maxOutputTokens": 800,
            }

            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, params=params, json=body)
            resp.raise_for_status()
            gen_resp = resp.json()

            # Extract text robustly
            answer_text = ""
            citations = None
            if "candidates" in gen_resp and gen_resp["candidates"]:
                cand = gen_resp["candidates"][0]
                # Many examples show the content under cand['content']['parts'][0]['text']
                content = cand.get("content") or cand.get("output") or cand.get("content")
                if isinstance(content, dict) and "parts" in content and content["parts"]:
                    answer_text = content["parts"][0].get("text", "")
                # fallback patterns:
                if not answer_text:
                    answer_text = cand.get("text") or cand.get("output_text") or ""

                # grounding/citation metadata:
                gm = cand.get("grounding_metadata") or cand.get("citation_metadata") or {}
                sources = gm.get("citation_sources") or gm.get("sources")
                if sources:
                    citations = []
                    for s in sources:
                        citations.append({
                            "uri": s.get("uri"),
                            "start_index": s.get("start_index"),
                            "end_index": s.get("end_index"),
                            "license": s.get("license")
                        })

            # final fallback: top-level response text
            if not answer_text:
                answer_text = gen_resp.get("output") or gen_resp.get("response") or ""

            return {"answer": answer_text, "citations": citations}
        except httpx.HTTPStatusError as he:
            logger.exception("HTTP error from generateContent: %s - %s", he.response.status_code, he.response.text)
            raise GeminiAPIException(f"Generate failed: {he.response.status_code} {he.response.text}")
        except Exception as e:
            logger.exception("Failed to search and generate via REST: %s", e)
            raise

    
    async def list_file_search_stores(self) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/fileSearchStores",
                    params={"key": self.api_key}
                )
                response.raise_for_status()
                data = response.json()
                
                stores = data.get('fileSearchStores', [])
                return [
                    {
                        "name": store.get("name"),
                        "display_name": store.get("displayName"),
                        "created_time": store.get("createTime"),
                        "update_time": store.get("updateTime")
                    }
                    for store in stores
                ]
        except Exception as e:
            logger.error(f"Failed to list file search stores: {e}")
            raise
    
    async def delete_file_search_store(self, store_name: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/{store_name}",
                    params={"key": self.api_key}
                )
                response.raise_for_status()
                logger.info(f"Deleted file search store: {store_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete file search store {store_name}: {e}")
            raise