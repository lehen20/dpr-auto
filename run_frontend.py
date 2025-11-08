#!/usr/bin/env python3
"""
Production-ready Streamlit frontend runner for document search application.
"""
import subprocess
import sys
import os

if __name__ == "__main__":
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "app.py")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", frontend_path,
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--theme.base=light"
    ])