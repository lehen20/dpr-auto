# Document Search Assistant

A production-grade chat-with-PDF application using Google Gemini's file-search capabilities, FastAPI backend, and Streamlit frontend.

## Features

- **Multi-format document support**: PDF, Word, Excel, PowerPoint, text files, and more
- **AI-powered search**: Powered by Google Gemini 2.5 Flash model
- **Citation tracking**: Get references to specific parts of your documents
- **Real-time chat interface**: Interactive Q&A with your documents
- **Production-ready**: Error handling, logging, validation, and Docker support
- **Scalable architecture**: Separate backend and frontend services

## Quick Start

### Prerequisites

- Python 3.8+
- Google AI Studio API key (get one at https://aistudio.google.com/app/apikey)

### Installation

1. Clone or download this project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

### Running the Application

1. **Start the backend** (in terminal 1):
   ```bash
   python run_backend.py
   ```
   Backend will be available at http://localhost:8000

2. **Start the frontend** (in terminal 2):
   ```bash
   python run_frontend.py
   ```
   Frontend will be available at http://localhost:8501

3. **Use the application**:
   - Upload documents via the sidebar
   - Ask questions in the chat interface
   - View citations and sources

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

### Key Endpoints

- `POST /upload` - Upload and index documents
- `POST /query` - Query documents with natural language
- `GET /health` - Health check
- `GET /stores` - List file search stores
- `DELETE /stores/{store_name}` - Delete a file search store

## Docker Deployment

### Build and run with Docker Compose:

```bash
docker-compose up --build
```

### Individual containers:

```bash
# Backend
docker build -f Dockerfile.backend -t doc-search-backend .
docker run -p 8000:8000 --env-file .env doc-search-backend

# Frontend
docker build -f Dockerfile.frontend -t doc-search-frontend .
docker run -p 8501:8501 doc-search-frontend
```

## Configuration

### Environment Variables

- `GOOGLE_API_KEY` - Your Google AI Studio API key (required)
- `BACKEND_URL` - Backend service URL (default: http://localhost:8000)
- `UPLOAD_DIR` - Directory for uploaded files (default: ./uploads)

### File Limits

- Maximum file size: 100MB
- Supported formats: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, JSON, CSV, XML, HTML, MD, RTF, TXT

## Architecture

```
┌─────────────────┐    HTTP/REST    ┌──────────────────┐
│  Streamlit      │ ───────────────► │  FastAPI         │
│  Frontend       │                  │  Backend         │
│  (Port 8501)    │                  │  (Port 8000)     │
└─────────────────┘                  └──────────────────┘
                                              │
                                              │ API Calls
                                              ▼
                                     ┌──────────────────┐
                                     │  Google Gemini   │
                                     │  File Search API │
                                     └──────────────────┘
```

## Production Considerations

- **Security**: API keys should be stored securely (use secrets management)
- **Scaling**: Backend can be horizontally scaled, consider load balancing
- **Monitoring**: Add application monitoring and logging
- **Rate Limits**: Implement rate limiting for public deployments
- **File Storage**: For production, consider cloud storage (S3, GCS) instead of local filesystem

## Troubleshooting

### Common Issues

1. **Backend not starting**: Check if port 8000 is available
2. **Frontend connection error**: Ensure backend is running and accessible
3. **Upload failures**: Verify file format and size limits
4. **API errors**: Check Google API key validity and quota

### Logs

- Backend logs: Check console output where backend is running
- Frontend logs: Check Streamlit interface and browser console

## License

MIT License - see LICENSE file for details.