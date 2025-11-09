import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import Settings, get_settings, ensure_upload_dir
from gemini_client import GeminiFileSearchClient
from models import (
    FileUploadResponse,
    QueryRequest,
    QueryResponse,
    HealthResponse,
    ErrorResponse,
    FileSearchStoreInfo,
    DataExtractionRequest,
    DataExtractionResponse,
    CertificateOfIncorporationData
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Search API",
    description="A production-grade API for document upload and AI-powered search using Gemini",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gemini_client: Optional[GeminiFileSearchClient] = None


@app.on_event("startup")
async def startup_event():
    global gemini_client
    settings = get_settings()
    ensure_upload_dir(settings.upload_dir)
    gemini_client = GeminiFileSearchClient(settings)
    logger.info("Application startup completed")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now()
    )


@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    store_name: Optional[str] = Form(None),
    settings: Settings = Depends(get_settings)
):
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type .{file_extension} not supported. Allowed types: {settings.allowed_extensions}"
            )
        
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_file_size / (1024*1024):.1f}MB"
            )
        
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = Path(settings.upload_dir) / safe_filename
        
        async with aiofiles.open(file_path, "wb") as buffer:
            content = await file.read()
            await buffer.write(content)
        
        operation_id = await gemini_client.upload_file(str(file_path), file.filename, store_name)
        
        logger.info(f"File {file.filename} uploaded successfully with ID {file_id}")
        
        return FileUploadResponse(
            success=True,
            message="File uploaded and indexed successfully",
            file_id=file_id,
            filename=file.filename,
            store_name=store_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = await gemini_client.search_and_generate(
            query=request.query,
            store_name=request.file_search_store_name
        )
        
        return QueryResponse(
            success=True,
            answer=result["answer"],
            citations=result.get("citations")
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return QueryResponse(
            success=False,
            answer="",
            error=f"Query processing failed: {str(e)}"
        )


@app.get("/stores")
async def list_file_search_stores():
    try:
        stores = await gemini_client.list_file_search_stores()
        return {"success": True, "stores": stores}
    except Exception as e:
        logger.error(f"Error listing stores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list stores: {str(e)}")


@app.delete("/stores/{store_name}")
async def delete_file_search_store(store_name: str):
    try:
        success = await gemini_client.delete_file_search_store(store_name)
        return {"success": success, "message": f"Store {store_name} deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting store: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete store: {str(e)}")


@app.post("/initialize_stores")
async def initialize_predefined_stores():
    """Initialize predefined file search stores."""
    try:
        predefined_stores = [
            "Certificate of Incorporation", 
            "MoA AoA", 
            "Machine Quotation"
        ]
        
        created_stores = []
        for store_display_name in predefined_stores:
            try:
                store_name = await gemini_client.get_or_create_store(store_display_name)
                created_stores.append({
                    "display_name": store_display_name,
                    "name": store_name
                })
            except Exception as e:
                logger.warning(f"Failed to create store {store_display_name}: {e}")
        
        return {"success": True, "stores": created_stores}
    except Exception as e:
        logger.error(f"Error initializing stores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize stores: {str(e)}")


@app.post("/extract_data", response_model=DataExtractionResponse)
async def extract_data(request: DataExtractionRequest):
    """Extract structured data from documents in a file search store."""
    try:
        extracted_data = await gemini_client.extract_structured_data(
            extraction_type=request.extraction_type,
            store_name=request.store_name
        )
        
        return DataExtractionResponse(
            success=True,
            extraction_type=request.extraction_type,
            data=extracted_data
        )
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        return DataExtractionResponse(
            success=False,
            extraction_type=request.extraction_type,
            error=f"Data extraction failed: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", detail=str(exc)).dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)