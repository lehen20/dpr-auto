import pdfplumber
import pytesseract
from PIL import Image
import re
from typing import List, Dict, Optional
from datetime import datetime
import json

from schemas import Segment, SegmentType, ExtractionField, SourceRef


def ocr_and_layout(file_path: str) -> List[Segment]:
    """Extract text segments from PDF using pdfplumber with pytesseract fallback"""
    segments = []
    
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # Try to extract text directly
            text = page.extract_text()
            
            if text and text.strip():
                # Split into paragraphs
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
                for para in paragraphs:
                    # Classify segment type based on formatting
                    if len(para) < 100 and (para.isupper() or para.startswith(('ARTICLE', 'CLAUSE', 'SECTION'))):
                        segment_type = SegmentType.HEADING
                    else:
                        segment_type = SegmentType.PARAGRAPH
                    
                    segments.append(Segment(
                        page=page_num + 1,
                        segment_type=segment_type,
                        text=para
                    ))
            
            # Extract tables
            try:
                tables = page.extract_tables()
                for table in tables:
                    if table:
                        table_text = '\n'.join(['\t'.join([str(cell) if cell else '' for cell in row]) for row in table])
                        segments.append(Segment(
                            page=page_num + 1,
                            segment_type=SegmentType.TABLE,
                            text=table_text
                        ))
            except:
                pass
    
    # If no text extracted, try OCR fallback
    if not segments:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img)
                
                if text.strip():
                    segments.append(Segment(
                        page=page_num + 1,
                        segment_type=SegmentType.PARAGRAPH,
                        text=text.strip()
                    ))
        except Exception as e:
            print(f"OCR fallback failed: {e}")
    
    return segments


def detect_doc_type(segments: List[Segment]) -> str:
    """Detect document type based on keyword heuristics"""
    text_content = ' '.join([seg.text.lower() for seg in segments])
    
    # Certificate of Incorporation keywords
    coi_keywords = ['certificate of incorporation', 'registrar of companies', 'corporate identity number', 'cin']
    
    # MoA/AoA keywords
    moa_keywords = ['memorandum of association', 'articles of association', 'authorized capital', 'main objects']
    
    coi_score = sum(1 for keyword in coi_keywords if keyword in text_content)
    moa_score = sum(1 for keyword in moa_keywords if keyword in text_content)
    
    if coi_score > moa_score:
        return "certificate_of_incorporation"
    elif moa_score > 0:
        return "moa_aoa"
    else:
        return "unknown"


def extract_incorporation_fields(segments: List[Segment], doc_id: str) -> Dict[str, ExtractionField]:
    """Extract fields specific to Certificate of Incorporation"""
    fields = {}
    
    # Extract company name
    name_field = extract_company_name(segments, doc_id)
    if name_field:
        fields['name'] = name_field
    
    # Extract CIN
    cin_field = extract_cin(segments, doc_id)
    if cin_field:
        fields['registration_number'] = cin_field
    
    # Extract company type
    type_field = extract_company_type(segments, doc_id)
    if type_field:
        fields['company_type'] = type_field
    
    # Extract formation date
    formation_date = extract_formation_date(segments, doc_id)
    if formation_date:
        fields['date_of_formation'] = formation_date
    
    # Extract registered office
    office_field = extract_registered_office(segments, doc_id)
    if office_field:
        fields['registered_office_address'] = office_field
    
    return fields


def extract_moa_aoa_fields(segments: List[Segment], doc_id: str) -> Dict[str, ExtractionField]:
    """Extract fields specific to MoA/AoA documents"""
    fields = {}
    
    # Extract authorized share capital
    capital_field = extract_authorized_capital(segments, doc_id)
    if capital_field:
        fields['authorized_share_capital'] = capital_field
    
    # Extract main objectives
    objectives_field = extract_main_objectives(segments, doc_id)
    if objectives_field:
        fields['main_objectives_raw'] = objectives_field
        # Auto-generate summary
        summary = objectives_field.value[:200] + "..." if len(objectives_field.value) > 200 else objectives_field.value
        fields['main_objectives_summary'] = ExtractionField(
            value=summary,
            confidence=0.8,
            source_refs=objectives_field.source_refs,
            raw_text=objectives_field.raw_text
        )
    
    # Extract board information
    board_field = extract_board_list(segments, doc_id)
    if board_field:
        fields['board_list'] = board_field
    
    # Extract shareholding schedule
    shareholding_field = extract_shareholding_schedule(segments, doc_id)
    if shareholding_field:
        fields['shareholding_schedule'] = shareholding_field
    
    # Check if MoA/AoA present
    fields['moa_aoa_present'] = ExtractionField(
        value=True,
        confidence=0.95,
        source_refs=[SourceRef(doc_id=doc_id, page=1, segment_type=SegmentType.PARAGRAPH, snippet="Document detected")],
        raw_text="MoA/AoA document detected"
    )
    
    return fields


def extract_company_name(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract company name from segments"""
    patterns = [
        r'(?:name of the company|company name)[:.]?\s*([A-Z][A-Z\s&.,()]+?)(?:\s+(?:limited|ltd|pvt|private))?(?:\s|$)',
        r'^([A-Z][A-Z\s&.,()]+?)\s+(?:LIMITED|LTD|PRIVATE LIMITED|PVT)',
        r'hereby certify that\s+([A-Z][A-Z\s&.,()]+?)\s+(?:LIMITED|LTD)'
    ]
    
    for segment in segments:
        if segment.segment_type == SegmentType.PARAGRAPH:
            for pattern in patterns:
                match = re.search(pattern, segment.text.upper())
                if match:
                    company_name = match.group(1).strip()
                    return ExtractionField(
                        value=company_name,
                        confidence=0.9,
                        source_refs=[SourceRef(
                            doc_id=doc_id,
                            page=segment.page,
                            segment_type=segment.segment_type,
                            snippet=segment.text[:200]
                        )],
                        raw_text=segment.text
                    )
    return None


def extract_cin(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract Corporate Identity Number"""
    cin_pattern = r'\b([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b'
    
    for segment in segments:
        match = re.search(cin_pattern, segment.text)
        if match:
            cin = match.group(1)
            return ExtractionField(
                value=cin,
                confidence=0.95,
                source_refs=[SourceRef(
                    doc_id=doc_id,
                    page=segment.page,
                    segment_type=segment.segment_type,
                    snippet=segment.text[:200]
                )],
                raw_text=segment.text
            )
    return None


def extract_company_type(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract company type (Private Limited, Public Limited, etc.)"""
    type_patterns = [
        r'(private limited|public limited|limited|one person company)',
        r'type of company[:.]?\s*([a-z\s]+)'
    ]
    
    for segment in segments:
        for pattern in type_patterns:
            match = re.search(pattern, segment.text.lower())
            if match:
                company_type = match.group(1).strip().title()
                return ExtractionField(
                    value=company_type,
                    confidence=0.85,
                    source_refs=[SourceRef(
                        doc_id=doc_id,
                        page=segment.page,
                        segment_type=segment.segment_type,
                        snippet=segment.text[:200]
                    )],
                    raw_text=segment.text
                )
    return None


def extract_formation_date(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract date of formation/incorporation"""
    date_patterns = [
        r'incorporated on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'date of incorporation[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4})'
    ]
    
    for segment in segments:
        for pattern in date_patterns:
            match = re.search(pattern, segment.text.lower())
            if match:
                date_str = normalize_date(match.group(1))
                if date_str:
                    return ExtractionField(
                        value=date_str,
                        confidence=0.9,
                        source_refs=[SourceRef(
                            doc_id=doc_id,
                            page=segment.page,
                            segment_type=segment.segment_type,
                            snippet=segment.text[:200]
                        )],
                        raw_text=segment.text
                    )
    return None


def extract_registered_office(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract registered office address"""
    for segment in segments:
        if 'registered office' in segment.text.lower():
            # Extract address after "registered office"
            text = segment.text.lower()
            start = text.find('registered office')
            if start != -1:
                # Extract next few lines as address
                address_text = segment.text[start:start+300]
                return ExtractionField(
                    value=address_text.strip(),
                    confidence=0.8,
                    source_refs=[SourceRef(
                        doc_id=doc_id,
                        page=segment.page,
                        segment_type=segment.segment_type,
                        snippet=segment.text[:200]
                    )],
                    raw_text=segment.text
                )
    return None


def extract_authorized_capital(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract authorized share capital"""
    capital_patterns = [
        r'authorized capital[:.]?\s*rs\.?\s*([\d,]+)',
        r'authorized share capital[:.]?\s*rs\.?\s*([\d,]+)',
        r'capital[:.]?\s*rs\.?\s*([\d,]+)\s*(?:lakhs?|crores?)?'
    ]
    
    for segment in segments:
        text = segment.text.lower()
        if 'authorized' in text and 'capital' in text:
            for pattern in capital_patterns:
                match = re.search(pattern, text)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    try:
                        amount = parse_currency_to_inr(amount_str)
                        return ExtractionField(
                            value={
                                "value": amount,
                                "unit": "INR",
                                "raw_text": segment.text
                            },
                            confidence=0.85,
                            source_refs=[SourceRef(
                                doc_id=doc_id,
                                page=segment.page,
                                segment_type=segment.segment_type,
                                snippet=segment.text[:200]
                            )],
                            raw_text=segment.text
                        )
                    except:
                        pass
    return None


def extract_main_objectives(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract main objectives/objects clause"""
    objective_texts = []
    
    for segment in segments:
        text = segment.text.lower()
        if any(keyword in text for keyword in ['main objects', 'principal objects', 'objects of the company']):
            objective_texts.append(segment.text)
    
    if objective_texts:
        combined_text = '\n\n'.join(objective_texts)
        return ExtractionField(
            value=combined_text,
            confidence=0.9,
            source_refs=[SourceRef(
                doc_id=doc_id,
                page=1,  # Simplified
                segment_type=SegmentType.PARAGRAPH,
                snippet=combined_text[:200]
            )],
            raw_text=combined_text
        )
    return None


def extract_board_list(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract board of directors list"""
    board_members = []
    
    for segment in segments:
        if segment.segment_type == SegmentType.TABLE:
            # Look for director tables
            lines = segment.text.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['director', 'chairman', 'managing director']):
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        board_members.append({
                            "name": parts[0].strip(),
                            "role": parts[1].strip() if len(parts) > 1 else "Director",
                            "raw_text": line
                        })
    
    if board_members:
        return ExtractionField(
            value=board_members,
            confidence=0.8,
            source_refs=[SourceRef(
                doc_id=doc_id,
                page=1,
                segment_type=SegmentType.TABLE,
                snippet="Board of Directors table"
            )],
            raw_text="Board information extracted from tables"
        )
    return None


def extract_shareholding_schedule(segments: List[Segment], doc_id: str) -> Optional[ExtractionField]:
    """Extract shareholding schedule"""
    shareholders = []
    
    for segment in segments:
        if segment.segment_type == SegmentType.TABLE:
            # Look for shareholding tables
            lines = segment.text.split('\n')
            for line in lines:
                if re.search(r'\d+.*shares?.*\d+%', line.lower()):
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        try:
                            shares_match = re.search(r'(\d+)', parts[1])
                            percent_match = re.search(r'(\d+(?:\.\d+)?)%', parts[2])
                            
                            shareholders.append({
                                "shareholder": parts[0].strip(),
                                "shares": int(shares_match.group(1)) if shares_match else 0,
                                "percentage": float(percent_match.group(1)) if percent_match else 0.0,
                                "raw_text": line
                            })
                        except:
                            pass
    
    if shareholders:
        return ExtractionField(
            value=shareholders,
            confidence=0.8,
            source_refs=[SourceRef(
                doc_id=doc_id,
                page=1,
                segment_type=SegmentType.TABLE,
                snippet="Shareholding schedule table"
            )],
            raw_text="Shareholding information extracted from tables"
        )
    return None


def normalize_date(text: str) -> Optional[str]:
    """Convert various date formats to ISO string"""
    date_patterns = [
        (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
        (r'(\d{1,2})(?:st|nd|rd|th)?\s+(\w+),?\s+(\d{4})', lambda m: format_month_date(m.group(1), m.group(2), m.group(3)))
    ]
    
    for pattern, formatter in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return formatter(match)
            except:
                pass
    
    return None


def format_month_date(day: str, month: str, year: str) -> str:
    """Convert month name to ISO format"""
    months = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }
    month_num = months.get(month.lower(), '01')
    return f"{year}-{month_num}-{day.zfill(2)}"


def parse_currency_to_inr(text: str) -> int:
    """Parse currency amount to INR integer"""
    # Remove commas and convert to number
    amount = float(re.sub(r'[,\s]', '', text))
    
    # Check for lakhs/crores multiplier
    if 'crore' in text.lower():
        amount *= 10000000  # 1 crore = 10 million
    elif 'lakh' in text.lower():
        amount *= 100000  # 1 lakh = 100 thousand
    
    return int(amount)


def find_table_by_header(segments: List[Segment], header_keywords: List[str]) -> Optional[Segment]:
    """Find table segment by header keywords"""
    for segment in segments:
        if segment.segment_type == SegmentType.TABLE:
            text = segment.text.lower()
            if any(keyword in text for keyword in header_keywords):
                return segment
    return None


if __name__ == "__main__":
    # Test functions
    print("Testing normalize_date:")
    print(normalize_date("15/03/2023"))  # Should output: 2023-03-15
    print(normalize_date("1st January, 2023"))  # Should output: 2023-01-01
    
    print("\nTesting parse_currency_to_inr:")
    print(parse_currency_to_inr("10,00,000"))  # Should output: 1000000
    print(parse_currency_to_inr("5 crores"))  # Should output: 50000000
    print(parse_currency_to_inr("15 lakhs"))  # Should output: 1500000