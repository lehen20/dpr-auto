#!/usr/bin/env python3
"""
Production-ready FastAPI backend runner for document search application.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import uvicorn
from backend.main import app

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )