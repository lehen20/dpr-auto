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
    
    async def create_file_search_store(self, display_name: str) -> str:
        """Create a new file search store with the given display name."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/fileSearchStores",
                    headers={"Content-Type": "application/json"},
                    params={"key": self.api_key},
                    json={"displayName": display_name}
                )
                response.raise_for_status()
                store = response.json()
                logger.info(f"Created file search store: {store['name']} ({display_name})")
                return store['name']
        except Exception as e:
            logger.error(f"Failed to create file search store {display_name}: {e}")
            raise
    
    async def get_or_create_store(self, display_name: str) -> str:
        """Get existing store by display name or create if not exists."""
        try:
            stores = await self.list_file_search_stores()
            for store in stores:
                if store['display_name'] == display_name:
                    return store['name']
            
            # Store doesn't exist, create it
            return await self.create_file_search_store(display_name)
        except Exception as e:
            logger.error(f"Failed to get or create store {display_name}: {e}")
            raise
    
    async def initialize_file_search_store(self) -> str:
        """Legacy method - creates default store."""
        return await self.get_or_create_store("Document Search Store")
    
    async def upload_file(self, file_path: str, filename: str, store_name: Optional[str] = None) -> str:
        try:
            if not store_name:
                store_name = await self.initialize_file_search_store()
            else:
                # Ensure the store exists
                stores = await self.list_file_search_stores()
                if not any(s['name'] == store_name for s in stores):
                    raise ValueError(f"Store {store_name} does not exist")
            
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
    
    async def extract_structured_data(self, extraction_type: str, store_name: str) -> Dict[str, Any]:
        """Extract structured data from documents using Gemini's structured output."""
        try:
            if extraction_type == "certificate_of_incorporation":
                # First try with structured output
                try:
                    return await self._extract_with_structured_output(extraction_type, store_name)
                except Exception as e:
                    logger.warning(f"Structured output failed: {e}, trying fallback method")
                    return await self._extract_with_fallback(extraction_type, store_name)
            elif extraction_type == "moa_aoa":
                # First try with structured output
                try:
                    return await self._extract_with_structured_output(extraction_type, store_name)
                except Exception as e:
                    logger.warning(f"Structured output failed: {e}, trying fallback method")
                    return await self._extract_with_fallback(extraction_type, store_name)
            else:
                raise ValueError(f"Unsupported extraction type: {extraction_type}")
            
        except Exception as e:
            logger.error(f"Failed to extract structured data: {e}")
            raise
    
    async def _extract_with_structured_output(self, extraction_type: str, store_name: str) -> Dict[str, Any]:
        """Try extraction with Gemini's structured output feature."""
        
        if extraction_type == "certificate_of_incorporation":
            prompt = """Extract the following information from the Certificate of Incorporation documents and return as JSON:
            
            Please return ONLY a valid JSON object with these exact keys:
            - company_name: The exact legal name of the company
            - registration_number: Company registration number or CIN
            - company_type: Type of company (Private Limited, Public Limited, LLP, etc.)
            - date_of_formation: Date of formation in ISO format (YYYY-MM-DD)
            - date_of_commencement: Date of commencement in ISO format (YYYY-MM-DD)
            - registered_office_address: Complete registered office address
            
            If any field is not found, use null as the value."""
            
            # JSON Schema for Certificate of Incorporation
            response_schema = {
                "type": "object",
                "properties": {
                    "company_name": {"type": ["string", "null"]},
                    "registration_number": {"type": ["string", "null"]},
                    "company_type": {"type": ["string", "null"]},
                    "date_of_formation": {"type": ["string", "null"]},
                    "date_of_commencement": {"type": ["string", "null"]},
                    "registered_office_address": {"type": ["string", "null"]}
                }
            }
            
        elif extraction_type == "moa_aoa":
            prompt = """Extract the following information from the Memorandum of Association (MoA) and Articles of Association (AoA) documents and return as JSON:
            
            Please return ONLY a valid JSON object with these exact keys:
            - authorized_share_capital: Object with {value: number, unit: "INR", raw_text: "original text"}
            - main_objectives_raw: Raw clause text of main objectives
            - main_objectives_summary: 1-2 sentence DPR-style summary (mark as autogenerated)
            - inclusiveness_policy_raw: Raw clause text about membership policies
            - inclusiveness_policy_summary: 1 sentence DPR-style summary (mark as autogenerated)
            - board_list: Array of {name: string, role: string, raw_text: string} for board members
            - shareholding_schedule: Array of {shareholder: string, shares: number, percentage: number} if present, else null
            - moa_aoa_present: Boolean true/false indicating if MoA/AoA documents are present
            
            If any field is not found, use null as the value. For summaries, include "(autogenerated)" at the end."""
            
            # JSON Schema for MoA AoA
            response_schema = {
                "type": "object",
                "properties": {
                    "authorized_share_capital": {
                        "type": ["object", "null"],
                        "properties": {
                            "value": {"type": ["number", "null"]},
                            "unit": {"type": "string", "default": "INR"},
                            "raw_text": {"type": ["string", "null"]}
                        }
                    },
                    "main_objectives_raw": {"type": ["string", "null"]},
                    "main_objectives_summary": {"type": ["string", "null"]},
                    "inclusiveness_policy_raw": {"type": ["string", "null"]},
                    "inclusiveness_policy_summary": {"type": ["string", "null"]},
                    "board_list": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": ["string", "null"]},
                                "role": {"type": ["string", "null"]},
                                "raw_text": {"type": ["string", "null"]}
                            }
                        }
                    },
                    "shareholding_schedule": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "shareholder": {"type": ["string", "null"]},
                                "shares": {"type": ["number", "null"]},
                                "percentage": {"type": ["number", "null"]}
                            }
                        }
                    },
                    "moa_aoa_present": {"type": ["boolean", "null"]}
                }
            }
        
        url = f"{self.base_url}/models/{self.settings.gemini_model}:generateContent"
        params = {"key": self.api_key}

        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"file_search": {"file_search_store_names": [store_name]}}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": response_schema
            }
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, params=params, json=body)
        resp.raise_for_status()
        gen_resp = resp.json()

        logger.info(f"Structured output response: {json.dumps(gen_resp, indent=2)}")
        
        if "candidates" in gen_resp and gen_resp["candidates"]:
            cand = gen_resp["candidates"][0]
            content = cand.get("content", {})
            if "parts" in content and content["parts"]:
                json_text = content["parts"][0].get("text", "")
                logger.info(f"Raw JSON from structured output: '{json_text}'")
                
                if json_text and json_text.strip():
                    try:
                        return json.loads(json_text.strip())
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON parse error in structured output: {e}")
                        raise
        
        raise Exception("No valid structured response")
    
    async def _extract_with_fallback(self, extraction_type: str, store_name: str) -> Dict[str, Any]:
        """Fallback extraction method using regular search."""
        
        if extraction_type == "certificate_of_incorporation":
            prompt = """Extract the following information from the Certificate of Incorporation documents:

            1. Company Name (exact legal name)
            2. Registration Number (CIN/registration identifier)  
            3. Company Type (Private Limited, Public Limited, LLP, etc.)
            4. Date of Formation (in ISO format YYYY-MM-DD)
            5. Date of Commencement (in ISO format YYYY-MM-DD)
            6. Registered Office Address (complete address)
            
            Please provide the response in this exact JSON format:
            {
                "company_name": "extracted company name or null",
                "registration_number": "extracted registration number or null",
                "company_type": "extracted company type or null", 
                "date_of_formation": "YYYY-MM-DD or null",
                "date_of_commencement": "YYYY-MM-DD or null",
                "registered_office_address": "extracted address or null"
            }
            
            Return ONLY the JSON, no other text."""
            
            default_response = {
                "company_name": None,
                "registration_number": None,
                "company_type": None,
                "date_of_formation": None,
                "date_of_commencement": None,
                "registered_office_address": None,
                "raw_response": None
            }
            
        elif extraction_type == "moa_aoa":
            prompt = """Extract the following information from the Memorandum of Association (MoA) and Articles of Association (AoA) documents:

            1. Authorized Share Capital (value, currency unit, and raw text)
            2. Main objectives clause (raw text and provide a 1-2 sentence DPR-style summary)
            3. Inclusiveness/membership policy (raw text and provide a 1 sentence DPR-style summary)
            4. Board of Directors list (names, roles, and raw text)
            5. Shareholding schedule if present (shareholder names, shares, percentages)
            6. Whether MoA/AoA documents are present
            
            Please provide the response in this exact JSON format:
            {
                "authorized_share_capital": {"value": number, "unit": "INR", "raw_text": "text or null"},
                "main_objectives_raw": "raw clause text or null",
                "main_objectives_summary": "1-2 sentence summary (autogenerated) or null",
                "inclusiveness_policy_raw": "raw clause text or null",
                "inclusiveness_policy_summary": "1 sentence summary (autogenerated) or null",
                "board_list": [{"name": "name", "role": "role", "raw_text": "text"} or null],
                "shareholding_schedule": [{"shareholder": "name", "shares": number, "percentage": number} or null],
                "moa_aoa_present": true/false
            }
            
            Return ONLY the JSON, no other text."""
            
            default_response = {
                "authorized_share_capital": None,
                "main_objectives_raw": None,
                "main_objectives_summary": None,
                "inclusiveness_policy_raw": None,
                "inclusiveness_policy_summary": None,
                "board_list": None,
                "shareholding_schedule": None,
                "moa_aoa_present": None,
                "raw_response": None
            }
        
        result = await self.search_and_generate(prompt, store_name)
        answer_text = result.get("answer", "")
        
        logger.info(f"Fallback method response: '{answer_text}'")
        
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', answer_text, re.DOTALL)
        if json_match:
            try:
                json_text = json_match.group().strip()
                return json.loads(json_text)
            except json.JSONDecodeError as e:
                logger.error(f"Fallback JSON parse error: {e}")
        
        # If no JSON found, return default with raw response
        default_response["raw_response"] = answer_text
        return default_response

    
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