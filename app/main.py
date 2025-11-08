from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import os
import uuid
from typing import List
import json
from datetime import datetime

from schemas import *
from extractors import ocr_and_layout, detect_doc_type, extract_incorporation_fields, extract_moa_aoa_fields
from store import save_doc, load_doc, save_project, load_project
from gemini_prompts import generate_text, dpr_synthesis_prompt

app = FastAPI(title="DPR Automation API", version="1.0.0")

# Ensure data directories exist
os.makedirs("./data/docs", exist_ok=True)
os.makedirs("./data/projects", exist_ok=True)


@app.post("/upload", response_model=List[DocumentIngestResponse])
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload one or more PDF documents"""
    responses = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"Only PDF files allowed: {file.filename}")
        
        doc_id = str(uuid.uuid4())
        file_path = f"./data/docs/{doc_id}.pdf"
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Count pages (simple estimate)
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                pages = len(reader.pages)
        except:
            pages = 1  # fallback
        
        # Save document metadata
        doc_metadata = {
            "doc_id": doc_id,
            "filename": file.filename,
            "file_path": file_path,
            "pages": pages,
            "upload_time": datetime.now().isoformat()
        }
        save_doc(doc_id, doc_metadata)
        
        responses.append(DocumentIngestResponse(
            doc_id=doc_id,
            filename=file.filename,
            pages=pages
        ))
    
    return responses


@app.post("/parse/{doc_id}", response_model=DocumentParseResponse)
async def parse_document(doc_id: str, background_tasks: BackgroundTasks):
    """Parse document to extract segments and page thumbnails"""
    doc_metadata = load_doc(doc_id)
    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc_metadata["file_path"]
    
    # Extract segments
    segments = ocr_and_layout(file_path)
    
    # Generate base64 page thumbnails (simplified)
    page_thumbnails = []
    for i in range(doc_metadata["pages"]):
        # Mock thumbnail - in real implementation, convert PDF page to image
        page_thumbnails.append(f"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    
    return DocumentParseResponse(
        doc_id=doc_id,
        segments=segments,
        page_thumbnails=page_thumbnails
    )


@app.post("/extract/{doc_id}", response_model=ExtractionResult)
async def extract_fields(doc_id: str):
    """Extract DPR-relevant fields from parsed document"""
    doc_metadata = load_doc(doc_id)
    if not doc_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = doc_metadata["file_path"]
    
    # Get segments
    segments = ocr_and_layout(file_path)
    
    # Detect document type
    doc_type = detect_doc_type(segments)
    
    # Extract fields based on document type
    if doc_type == "certificate_of_incorporation":
        fields = extract_incorporation_fields(segments, doc_id)
    elif doc_type == "moa_aoa":
        fields = extract_moa_aoa_fields(segments, doc_id)
    else:
        fields = {}
    
    return ExtractionResult(
        doc_id=doc_id,
        doc_type=doc_type,
        fields=fields,
        extraction_time=datetime.now()
    )


@app.post("/merge/{project_id}", response_model=MergeResponse)
async def merge_extractions(project_id: str, doc_ids: List[str]):
    """Merge extracted fields from multiple documents into DPR JSON"""
    
    # Load existing project or create new
    try:
        dpr = load_project(project_id)
    except:
        dpr = DPR(
            project_id=project_id,
            extraction_time=datetime.now(),
            documents=[],
            spv=SPVInfo(),
            promoters=[],
            extraction_summary=ExtractionSummary(
                fields_extracted=0,
                fields_missing=[],
                validation_warnings=[]
            )
        )
    
    # Merge fields from all documents
    all_fields = {}
    for doc_id in doc_ids:
        if doc_id not in dpr.documents:
            dpr.documents.append(doc_id)
        
        # Load extraction result for this document
        doc_metadata = load_doc(doc_id)
        if doc_metadata:
            file_path = doc_metadata["file_path"]
            segments = ocr_and_layout(file_path)
            doc_type = detect_doc_type(segments)
            
            if doc_type == "certificate_of_incorporation":
                fields = extract_incorporation_fields(segments, doc_id)
            elif doc_type == "moa_aoa":
                fields = extract_moa_aoa_fields(segments, doc_id)
            else:
                fields = {}
            
            all_fields.update(fields)
    
    # Map fields to SPV structure
    spv = SPVInfo()
    for field_name, field_data in all_fields.items():
        if hasattr(spv, field_name):
            setattr(spv, field_name, field_data)
    
    dpr.spv = spv
    dpr.extraction_time = datetime.now()
    
    # Update extraction summary
    extracted_fields = [k for k, v in all_fields.items() if v and v.value is not None]
    missing_fields = [k for k in ['name', 'registration_number', 'company_type'] if k not in extracted_fields]
    warnings = [f"Field {k} has low confidence" for k, v in all_fields.items() if v and v.confidence < 0.85]
    
    dpr.extraction_summary = ExtractionSummary(
        fields_extracted=len(extracted_fields),
        fields_missing=missing_fields,
        validation_warnings=warnings
    )
    
    # Save merged DPR
    save_project(project_id, dpr.dict())
    
    return MergeResponse(
        project_id=project_id,
        merged_dpr=dpr
    )


@app.post("/dpr/{project_id}/update_field")
async def update_field(project_id: str, request: UpdateFieldRequest):
    """Update a specific field in the DPR with human edits"""
    dpr_data = load_project(project_id)
    if not dpr_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    dpr = DPR(**dpr_data)
    
    # Navigate to field using dot notation
    field_parts = request.field_path.split('.')
    obj = dpr
    
    for part in field_parts[:-1]:
        obj = getattr(obj, part)
    
    # Update field value
    if hasattr(obj, field_parts[-1]):
        current_field = getattr(obj, field_parts[-1])
        if current_field and isinstance(current_field, ExtractionField):
            current_field.value = request.new_value
            current_field.confidence = min(current_field.confidence + 0.1, 1.0)  # Boost confidence after human review
            current_field.needs_review = False
    
    # Save updated DPR
    save_project(project_id, dpr.dict())
    
    return {"status": "updated", "field_path": request.field_path}


@app.post("/dpr/{project_id}/generate", response_model=DPRGenerateResponse)
async def generate_dpr_draft(project_id: str):
    """Generate DPR draft sections using Gemini"""
    dpr_data = load_project(project_id)
    if not dpr_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    dpr = DPR(**dpr_data)
    
    # Prepare context for Gemini
    context = {
        "spv_name": dpr.spv.name.value if dpr.spv.name else "N/A",
        "registration_number": dpr.spv.registration_number.value if dpr.spv.registration_number else "N/A",
        "company_type": dpr.spv.company_type.value if dpr.spv.company_type else "N/A",
        "main_objectives": dpr.spv.main_objectives_raw.value if dpr.spv.main_objectives_raw else "N/A"
    }
    
    # Generate using Gemini
    prompt = dpr_synthesis_prompt.format(**context)
    response_text = generate_text(prompt, max_tokens=1024)
    
    # Parse response (simplified)
    try:
        response_data = json.loads(response_text)
        sections = [DPRSection(**section) for section in response_data.get("sections", [])]
    except:
        # Fallback if JSON parsing fails
        sections = [
            DPRSection(
                id="proposal",
                title="Proposal",
                body=f"This DPR proposes the establishment of {context['spv_name']} ({context['registration_number']}).",
                source_refs=["Generated by Gemini"]
            )
        ]
    
    dpr_text = "\n\n".join([f"## {section.title}\n{section.body}" for section in sections])
    
    return DPRGenerateResponse(
        dpr_text=dpr_text,
        sections=sections
    )


@app.get("/dpr/{project_id}", response_model=DPR)
async def get_dpr(project_id: str):
    """Retrieve stored DPR JSON and extraction summary"""
    dpr_data = load_project(project_id)
    if not dpr_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return DPR(**dpr_data)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)