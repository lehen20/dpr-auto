from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: Optional[str] = None
    filename: Optional[str] = None
    store_name: Optional[str] = None


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


class DataExtractionRequest(BaseModel):
    store_name: str
    extraction_type: str  # 'certificate_of_incorporation', 'moa_aoa', 'machine_quotation'


class CertificateOfIncorporationData(BaseModel):
    company_name: Optional[str] = None
    registration_number: Optional[str] = None
    company_type: Optional[str] = None
    date_of_formation: Optional[str] = None  # ISO format
    date_of_commencement: Optional[str] = None
    registered_office_address: Optional[str] = None


class AuthorizedShareCapital(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = "INR"
    raw_text: Optional[str] = None


class BoardMember(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    raw_text: Optional[str] = None


class ShareholderInfo(BaseModel):
    shareholder: Optional[str] = None
    shares: Optional[int] = None
    percentage: Optional[float] = None


class MoAAoAData(BaseModel):
    authorized_share_capital: Optional[AuthorizedShareCapital] = None
    main_objectives_raw: Optional[str] = None
    main_objectives_summary: Optional[str] = None
    inclusiveness_policy_raw: Optional[str] = None
    inclusiveness_policy_summary: Optional[str] = None
    board_list: Optional[List[BoardMember]] = None
    shareholding_schedule: Optional[List[ShareholderInfo]] = None
    moa_aoa_present: Optional[bool] = None


class DataExtractionResponse(BaseModel):
    success: bool
    extraction_type: str
    data: Optional[dict] = None
    error: Optional[str] = None