from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    filename: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    file_search_store_name: Optional[str] = None


class QueryResponse(BaseModel):
    success: bool
    answer: str
    citations: Optional[List[dict]] = None
    error: Optional[str] = None


class FileSearchStoreInfo(BaseModel):
    name: str
    display_name: str
    created_time: datetime
    update_time: datetime


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None