# DPR Field Extraction Specifications

## Overview
This document defines the extraction patterns, confidence rules, and Human-in-the-Loop (HITL) guidelines for processing Certificate of Incorporation (CoI) and Memorandum & Articles of Association (MoA/AoA) documents.

## Document Types

### Certificate of Incorporation (CoI)
**Identification Keywords:**
- "certificate of incorporation"
- "registrar of companies"
- "corporate identity number"
- "cin"
- "company incorporated"

### Memorandum & Articles of Association (MoA/AoA)
**Identification Keywords:**
- "memorandum of association"
- "articles of association"
- "authorized capital"
- "main objects"
- "objects of the company"

## Field Extraction Patterns

### 1. Company Name
**Sources:** CoI, MoA/AoA
**Patterns:**
```regex
(?:name of the company|company name)[:.]?\s*([A-Z][A-Z\s&.,()]+?)(?:\s+(?:limited|ltd|pvt|private))?(?:\s|$)
^([A-Z][A-Z\s&.,()]+?)\s+(?:LIMITED|LTD|PRIVATE LIMITED|PVT)
hereby certify that\s+([A-Z][A-Z\s&.,()]+?)\s+(?:LIMITED|LTD)
```
**Confidence Rules:**
- Exact match with company suffixes: 0.95
- Pattern match in heading: 0.90
- Pattern match in paragraph: 0.85

### 2. Corporate Identity Number (CIN)
**Sources:** CoI
**Pattern:**
```regex
\b([UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b
```
**Format:** `U/L + 5 digits + 2 letters + 4 digits + 3 letters + 6 digits`
**Examples:**
- `U51909DL2023PTC123456`
- `L74999MH2022PLC234567`

**Confidence:** 0.95 (format is standardized)

### 3. Company Type
**Sources:** CoI, MoA/AoA
**Patterns:**
```regex
(private limited|public limited|limited|one person company)
type of company[:.]?\s*([a-z\s]+)
```
**Values:**
- Private Limited Company
- Public Limited Company  
- One Person Company
- Limited Liability Partnership

**Confidence:** 0.85

### 4. Date of Formation/Incorporation
**Sources:** CoI
**Patterns:**
```regex
incorporated on\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})
date of incorporation[:.]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})
(\d{1,2}(?:st|nd|rd|th)?\s+\w+,?\s+\d{4})
```
**Output Format:** ISO 8601 (YYYY-MM-DD)
**Confidence:** 0.90

### 5. Registered Office Address
**Sources:** CoI, MoA/AoA
**Anchor Text:** "registered office"
**Extraction:** Next 2-3 lines after anchor
**Confidence:** 0.80

### 6. Authorized Share Capital
**Sources:** MoA/AoA
**Patterns:**
```regex
authorized capital[:.]?\s*rs\.?\s*([\d,]+)
authorized share capital[:.]?\s*rs\.?\s*([\d,]+)
capital[:.]?\s*rs\.?\s*([\d,]+)\s*(?:lakhs?|crores?)?
```
**Currency Conversion:**
- 1 lakh = 100,000
- 1 crore = 10,000,000
**Output:** Integer in INR
**Confidence:** 0.85

### 7. Main Objects/Objectives
**Sources:** MoA/AoA
**Anchor Text:**
- "main objects"
- "principal objects"
- "objects of the company"
- "object clause"

**Extraction:** Capture entire clause section
**Auto-Summary:** Generate 40-word summary using Gemini
**Confidence:** 0.90

### 8. Board of Directors
**Sources:** AoA, Director list tables
**Table Headers:**
- "director"
- "name"
- "designation"
- "din"

**Structure:**
```json
{
  "name": "string",
  "role": "string", 
  "din": "string (optional)",
  "raw_text": "string"
}
```
**Confidence:** 0.80

### 9. Shareholding Schedule
**Sources:** MoA/AoA tables
**Table Headers:**
- "shareholder"
- "shares"
- "percentage"
- "equity"

**Structure:**
```json
{
  "shareholder": "string",
  "shares": "integer",
  "percentage": "float",
  "raw_text": "string"
}
```
**Confidence:** 0.80

## Date Normalization Patterns

### Input Formats
```regex
# DD/MM/YYYY or DD-MM-YYYY
(\d{1,2})[/-](\d{1,2})[/-](\d{4})

# DD Month, YYYY
(\d{1,2})(?:st|nd|rd|th)?\s+(\w+),?\s+(\d{4})
```

### Month Mapping
```json
{
  "january": "01", "february": "02", "march": "03",
  "april": "04", "may": "05", "june": "06",
  "july": "07", "august": "08", "september": "09", 
  "october": "10", "november": "11", "december": "12"
}
```

## Currency Parsing Rules

### Input Patterns
```regex
# Basic amount
rs\.?\s*([\d,]+)

# With multipliers
([\d,\.]+)\s*(lakhs?|crores?)

# Spelled out
(one|two|three|four|five|six|seven|eight|nine|ten)\s+(lakhs?|crores?)
```

### Conversion Logic
1. Remove commas and spaces
2. Convert to float
3. Apply multiplier:
   - lakh: × 100,000
   - crore: × 10,000,000
4. Convert to integer INR

## Confidence Scoring Rules

### High Confidence (0.90-1.00)
- Exact regex match in structured format (CIN, dates)
- Table-based extraction with clear headers
- Standardized fields with validation

### Medium Confidence (0.75-0.89)
- Pattern match in headings/titles
- Clear contextual anchors
- Manual verification recommended

### Low Confidence (0.50-0.74)
- Pattern match in general text
- Ambiguous context
- Requires human review

### Confidence Adjustments
- **LLM Enhancement:** -0.05 from base confidence
- **Multiple sources:** +0.05 per additional source
- **Manual verification:** Set to 1.00
- **Human edit:** +0.10 (max 1.00)

## Human-in-the-Loop (HITL) Rules

### Automatic Flagging
Fields requiring human review when:
- Confidence < 0.85
- Multiple conflicting values found
- Critical fields missing (name, CIN, company type)
- Format validation fails

### Review Priority
1. **Critical:** Company name, CIN, company type
2. **Important:** Formation date, authorized capital, main objects  
3. **Optional:** Board list, shareholding schedule, office address

### Validation Warnings
- Invalid CIN format
- Future incorporation dates
- Unrealistic capital amounts (< 100 or > 10 crores)
- Missing mandatory fields

## Table Extraction Guidelines

### Table Detection
Look for:
- Consistent column alignment
- Header rows with keywords
- Tabular data patterns
- Cell separators (|, tabs, multiple spaces)

### Supported Table Types
1. **Director Information**
   - Headers: Name, Designation, DIN, Address
   - Confidence: 0.80

2. **Shareholding Details**  
   - Headers: Shareholder, Shares, Percentage, Class
   - Confidence: 0.80

3. **Capital Structure**
   - Headers: Class, Authorized, Issued, Paid-up
   - Confidence: 0.85

### Table Processing
1. Identify table boundaries
2. Extract headers and data rows
3. Map columns to fields
4. Validate data types
5. Generate structured output

## Error Handling

### Common Issues
1. **OCR Errors:** Use confidence-based fallback
2. **Format Variations:** Multiple pattern attempts
3. **Missing Data:** Mark as null with source reference
4. **Conflicting Data:** Preserve all sources, flag for review

### Fallback Strategies
1. Try alternative regex patterns
2. Use fuzzy string matching
3. LLM-assisted extraction for complex cases
4. Manual review queue for unresolved items

## Output Schema Compliance

### Required Source References
Every extracted field must include:
```json
{
  "value": "extracted_value",
  "confidence": 0.85,
  "source_refs": [{
    "doc_id": "document_id", 
    "page": 2,
    "segment_type": "paragraph",
    "snippet": "first 200 chars of source text"
  }],
  "raw_text": "full source text",
  "needs_review": false
}
```

### Field Validation
- Company name: 1-100 characters, title case
- CIN: Exact 21-character format
- Dates: Valid ISO 8601 format
- Amounts: Positive integers
- Percentages: 0.0-100.0 range

## Performance Targets

### Accuracy Goals
- **Structured fields (CIN, dates):** > 95%
- **Standard fields (name, type):** > 90% 
- **Complex fields (objectives):** > 85%
- **Table data:** > 80%

### Processing Speed
- Document parsing: < 30 seconds
- Field extraction: < 60 seconds  
- Total pipeline: < 5 minutes per document

### Review Rate
- Target: < 20% of fields requiring human review
- Critical fields: < 10% review rate
- Complex extractions: < 30% review rate