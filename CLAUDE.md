# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a production-grade document search application with a microservices architecture:

- **Backend**: FastAPI service (`backend/main.py`) providing REST API for document upload and AI-powered search
- **Frontend**: Streamlit web interface (`frontend/app.py`) for user interactions
- **AI Integration**: Google Gemini 2.5 Flash model with file search capabilities via `GeminiFileSearchClient`

### Key Components

- `backend/main.py` - FastAPI application with CORS middleware, file upload handling, and search endpoints
- `backend/gemini_client.py` - Wrapper for Google Gemini file search API
- `backend/config.py` - Pydantic settings with environment variable support
- `backend/models.py` - Pydantic models for request/response validation
- `frontend/app.py` - Streamlit interface for document upload and chat

## Development Commands

### Starting Services

Start backend (port 8000):
```bash
python run_backend.py
```

Start frontend (port 8501):
```bash
python run_frontend.py
```

### Setup Commands

Install dependencies:
```bash
pip install -r requirements.txt
```

Run setup script (creates venv, installs deps, creates uploads dir):
```bash
./start.sh
```

### Environment Setup

Copy environment template and configure Google API key:
```bash
cp .env.example .env
# Edit .env to add GOOGLE_API_KEY
```

## API Endpoints

- `POST /upload` - Upload and index documents (supports PDF, DOC, XLS, PPT, TXT, JSON, etc.)
- `POST /query` - Query documents with natural language
- `GET /health` - Health check
- `GET /stores` - List Gemini file search stores
- `DELETE /stores/{store_name}` - Delete file search store

## Configuration

Environment variables in `.env`:
- `GOOGLE_API_KEY` - Required Google AI Studio API key
- `BACKEND_URL` - Backend service URL (default: http://localhost:8000)
- `UPLOAD_DIR` - File upload directory (default: ./uploads)

File constraints:
- Max size: 100MB
- Allowed formats: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, JSON, CSV, XML, HTML, MD, RTF, TXT

## File Structure

- `run_backend.py` / `run_frontend.py` - Service runners with uvicorn/streamlit configuration
- `backend/` - FastAPI backend with config, models, exceptions, and Gemini client
- `frontend/` - Streamlit frontend application
- `uploads/` - Local file storage directory (created automatically)
- `requirements.txt` - Python dependencies