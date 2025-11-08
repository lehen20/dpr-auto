# DPR Automation Tool

🤖 AI-powered system for extracting DPR-relevant fields from Certificate of Incorporation (CoI) and Memorandum & Articles of Association (MoA/AoA) documents.

## Features

- **PDF Document Processing**: OCR and layout analysis using pdfplumber/pytesseract
- **Intelligent Field Extraction**: Regex and NER-based extraction with confidence scoring  
- **Human-in-the-Loop Editing**: Review and edit extracted fields through web interface
- **AI-Powered Summarization**: Gemini LLM integration for generating DPR drafts
- **Workflow Management**: LangGraph workflow orchestration
- **REST API**: FastAPI backend with comprehensive endpoints
- **Interactive Frontend**: Streamlit web interface for document processing

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Streamlit     │    │    FastAPI       │    │   PDF Files     │
│   Frontend      │◄──►│    Backend       │◄──►│   Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Extractors     │
                       │  (OCR + Regex)   │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Gemini LLM      │
                       │  (Summarization) │
                       └──────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd dpr-auto

# Install dependencies
pip install -r requirements.txt

# Install Tesseract OCR (if not already installed)
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr

# macOS:
brew install tesseract

# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Environment Setup

```bash
# Create .env file (optional)
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env

# Note: If no API key is provided, the system will use mock responses
```

### 3. Run the Application

**Start Backend API:**
```bash
# Terminal 1
cd dpr-auto
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Frontend:**
```bash
# Terminal 2  
cd dpr-auto
streamlit run streamlit_app.py --server.port 8501
```

**Access the Application:**
- Frontend: http://localhost:8501
- API Documentation: http://localhost:8000/docs

## Usage Guide

### 1. Upload Documents
- Navigate to "📤 Upload Documents"
- Upload one or more PDF files (CoI, MoA/AoA)
- System automatically assigns document IDs

### 2. Parse and Extract
- Go to "📋 Review Documents" 
- Click "Parse" to extract text segments and page thumbnails
- Click "Extract Fields" to run field extraction with confidence scores

### 3. Human Review and Editing
- Visit "✏️ Edit Fields"
- Review extracted fields with confidence indicators
- Edit field values as needed (automatically boosts confidence)
- Fields with confidence < 0.85 are flagged for review

### 4. Merge and Generate DPR
- Navigate to "🔄 Merge & Generate"
- Click "Merge Extracted Fields" to consolidate data from multiple documents
- Click "Generate DPR Draft" to create formatted sections using Gemini AI
- Download results as text or JSON

### 5. Review Final Output
- Check "📊 View DPR" for complete merged data
- Validation warnings highlight missing or low-confidence fields

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload PDF documents |
| `/parse/{doc_id}` | POST | Parse document segments |
| `/extract/{doc_id}` | POST | Extract structured fields |
| `/merge/{project_id}` | POST | Merge fields from multiple docs |
| `/dpr/{project_id}/update_field` | POST | Update specific field |
| `/dpr/{project_id}/generate` | POST | Generate DPR draft |
| `/dpr/{project_id}` | GET | Retrieve project data |
| `/health` | GET | API health check |

## Supported Fields

### Certificate of Incorporation
- Company Name
- Corporate Identity Number (CIN) 
- Company Type
- Date of Formation
- Registered Office Address

### MoA/AoA Documents  
- Authorized Share Capital
- Main Objectives (raw + summary)
- Inclusiveness Policy (raw + summary)
- Board of Directors List
- Shareholding Schedule

## Configuration

### Environment Variables
```bash
GEMINI_API_KEY=your_api_key_here  # Optional, uses mock if not set
```

### File Structure
```
dpr-auto/
├── app/
│   ├── main.py              # FastAPI application
│   ├── schemas.py           # Pydantic models
│   ├── extractors.py        # PDF processing and field extraction
│   ├── gemini_prompts.py    # LLM integration
│   ├── langgraph_workflow.py # Workflow definition
│   ├── store.py            # File storage
│   └── weaviate_client.py  # Vector DB stub (optional)
├── data/
│   ├── docs/               # Uploaded PDF files + metadata
│   └── projects/           # Project DPR JSON files
├── specs/
│   └── extraction_spec.md  # Field extraction specifications
├── examples/
│   ├── sample_input.json   # Sample document structure
│   └── sample_output.json  # Sample extraction result
├── streamlit_app.py        # Frontend application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Confidence Scoring

| Range | Description | Action Required |
|-------|-------------|-----------------|
| 0.90-1.00 | High confidence | Auto-accept |
| 0.75-0.89 | Medium confidence | Optional review |
| 0.50-0.74 | Low confidence | Manual review required |
| 0.00-0.49 | Very low confidence | Manual entry recommended |

## Testing

### Test Extraction Functions
```bash
# Test PDF extraction and currency parsing
python app/extractors.py

# Test Gemini integration
python app/gemini_prompts.py

# Test file store
python app/store.py
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Upload test document
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@test_document.pdf"
```

## Troubleshooting

### Common Issues

**1. Tesseract not found**
```bash
# Install tesseract-ocr package for your OS
# Set TESSDATA_PREFIX environment variable if needed
```

**2. PDF parsing fails**
```bash
# Check PDF is not password protected
# Ensure sufficient disk space in ./data directory
```

**3. API connection error**
```bash
# Verify FastAPI server is running on port 8000
# Check firewall settings
```

**4. Low extraction accuracy**
```bash
# Review specs/extraction_spec.md for supported formats
# Use human review for complex documents
# Consider improving regex patterns in extractors.py
```

### Performance Optimization

- **Large PDFs**: Process in chunks or increase timeout limits
- **Multiple documents**: Use parallel processing where possible  
- **Memory usage**: Monitor for large document batches
- **API rate limits**: Implement backoff for Gemini API calls

## Development

### Adding New Fields
1. Update `schemas.py` with new field definitions
2. Add extraction patterns to `extractors.py`
3. Update extraction specifications in `specs/extraction_spec.md`
4. Test with sample documents

### Extending LLM Integration
1. Modify `gemini_prompts.py` templates
2. Add new prompt functions as needed
3. Update API endpoints in `main.py`
4. Test with different document types

## Security Considerations

- API keys stored in environment variables only
- No sensitive data logged to console
- Uploaded files stored locally (consider encryption for production)
- Input validation on all API endpoints
- File type restrictions enforced

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please create a GitHub issue with:
- Description of the problem
- Sample input files (anonymized)
- Expected vs actual output
- System environment details