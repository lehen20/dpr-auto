from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class SegmentType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"


class Segment(BaseModel):
    page: int
    segment_type: SegmentType
    text: str
    bbox: Optional[List[float]] = None


class SourceRef(BaseModel):
    doc_id: str
    page: int
    segment_type: SegmentType
    snippet: str = Field(..., max_length=200)


class ExtractionField(BaseModel):
    value: Union[str, int, bool, List[Dict[str, Any]], None]
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_refs: List[SourceRef]
    raw_text: Optional[str] = None
    needs_review: bool = Field(default=False)


class DocumentIngestResponse(BaseModel):
    doc_id: str
    filename: str
    pages: int
    status: str = "uploaded"


class DocumentParseResponse(BaseModel):
    doc_id: str
    segments: List[Segment]
    page_thumbnails: List[str]  # base64 encoded


class BoardMember(BaseModel):
    name: str
    role: str
    raw_text: str


class Shareholder(BaseModel):
    shareholder: str
    shares: int
    percentage: float
    raw_text: str


class ShareCapital(BaseModel):
    value: int  # in INR
    unit: str = "INR"
    raw_text: str


class SPVInfo(BaseModel):
    name: Optional[ExtractionField] = None
    registration_number: Optional[ExtractionField] = None
    company_type: Optional[ExtractionField] = None
    date_of_formation: Optional[ExtractionField] = None
    date_of_commencement: Optional[ExtractionField] = None
    registered_office_address: Optional[ExtractionField] = None
    authorized_share_capital: Optional[ExtractionField] = None
    main_objectives_raw: Optional[ExtractionField] = None
    main_objectives_summary: Optional[ExtractionField] = None
    inclusiveness_policy_raw: Optional[ExtractionField] = None
    inclusiveness_policy_summary: Optional[ExtractionField] = None
    board_list: Optional[ExtractionField] = None
    shareholding_schedule: Optional[ExtractionField] = None
    moa_aoa_present: Optional[ExtractionField] = None


class ExtractionSummary(BaseModel):
    fields_extracted: int
    fields_missing: List[str]
    validation_warnings: List[str]


class ExtractionResult(BaseModel):
    doc_id: str
    doc_type: str
    fields: Dict[str, ExtractionField]
    extraction_time: datetime


class DPR(BaseModel):
    project_id: str
    extraction_time: datetime
    documents: List[str]
    spv: SPVInfo
    promoters: List[Dict[str, Any]] = []
    extraction_summary: ExtractionSummary


class UpdateFieldRequest(BaseModel):
    field_path: str
    new_value: Union[str, int, bool, List[Dict[str, Any]], None]
    user_id: str


class MergeResponse(BaseModel):
    project_id: str
    merged_dpr: DPR
    status: str = "merged"


class DPRSection(BaseModel):
    id: str
    title: str
    body: str
    source_refs: List[str]


class DPRGenerateResponse(BaseModel):
    dpr_text: str
    sections: List[DPRSection]