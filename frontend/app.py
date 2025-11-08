import streamlit as st
import requests
import json
from typing import Optional
import os
from datetime import datetime

# BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_URL = "http://localhost:8000"


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []


def upload_file(file) -> Optional[dict]:
    try:
        files = {"file": (file.name, file, file.type)}
        response = requests.post(f"{BACKEND_URL}/upload", files=files, timeout=300)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during upload: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during upload: {str(e)}")
        return None


def query_documents(query: str) -> Optional[dict]:
    try:
        payload = {"query": query}
        response = requests.post(
            f"{BACKEND_URL}/query",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Query failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during query: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during query: {str(e)}")
        return None


def check_backend_health() -> bool:
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    st.set_page_config(
        page_title="Document Search Assistant",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    initialize_session_state()
    
    st.title("📚 Document Search Assistant")
    st.markdown("Upload documents and ask questions about their content using AI.")
    
    if not check_backend_health():
        st.error("⚠️ Backend service is not available. Please ensure the FastAPI server is running.")
        st.stop()
    
    with st.sidebar:
        st.header("📁 File Upload")
        
        uploaded_file = st.file_uploader(
            "Choose a document",
            type=["pdf", "txt", "doc", "docx", "xls", "xlsx", "ppt", "pptx", 
                  "json", "csv", "xml", "html", "md", "rtf"],
            help="Supported formats: PDF, Word, Excel, PowerPoint, Text files, and more (Max: 100MB)"
        )
        
        if uploaded_file is not None:
            # Check if file was already uploaded
            file_already_uploaded = any(
                f["filename"] == uploaded_file.name 
                for f in st.session_state.uploaded_files
            )
            
            if not file_already_uploaded:
                with st.spinner("Uploading and indexing document..."):
                    result = upload_file(uploaded_file)
                    
                    if result and result.get("success"):
                        st.success(f"✅ {result['filename']} uploaded successfully!")
                        st.session_state.uploaded_files.append({
                            "filename": result["filename"],
                            "file_id": result["file_id"],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
            else:
                st.info(f"📄 {uploaded_file.name} is already uploaded")
        
        if st.session_state.uploaded_files:
            st.subheader("📋 Uploaded Files")
            for i, file_info in enumerate(st.session_state.uploaded_files):
                with st.expander(f"{file_info['filename']}", expanded=False):
                    st.write(f"**File ID:** {file_info['file_id'][:8]}...")
                    st.write(f"**Uploaded:** {file_info['timestamp']}")
                    
                    if st.button(f"Remove", key=f"remove_{i}"):
                        st.session_state.uploaded_files.pop(i)
                        st.rerun()
        
        if st.button("🗑️ Clear All Files"):
            st.session_state.uploaded_files = []
            st.rerun()
        
        if st.button("🔄 Clear Chat History"):
            st.session_state.messages = []
            st.rerun()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("💬 Chat Interface")
        
        if not st.session_state.uploaded_files:
            st.info("👆 Please upload a document first to start asking questions.")
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                if message["role"] == "assistant" and "citations" in message:
                    if message["citations"]:
                        with st.expander("📖 Citations", expanded=False):
                            for i, citation in enumerate(message["citations"]):
                                st.write(f"**Citation {i+1}:**")
                                if citation.get("uri"):
                                    st.write(f"- Source: {citation['uri']}")
                                st.write(f"- Text range: {citation.get('start_index', 'N/A')} - {citation.get('end_index', 'N/A')}")
                                if citation.get("license"):
                                    st.write(f"- License: {citation['license']}")
                                st.divider()
        
        if prompt := st.chat_input("Ask a question about your documents...", disabled=not st.session_state.uploaded_files):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = query_documents(prompt)
                    
                    if response and response.get("success"):
                        answer = response["answer"]
                        citations = response.get("citations")
                        
                        st.markdown(answer)
                        
                        message_data = {
                            "role": "assistant",
                            "content": answer
                        }
                        
                        if citations:
                            message_data["citations"] = citations
                            with st.expander("📖 Citations", expanded=False):
                                for i, citation in enumerate(citations):
                                    st.write(f"**Citation {i+1}:**")
                                    if citation.get("uri"):
                                        st.write(f"- Source: {citation['uri']}")
                                    st.write(f"- Text range: {citation.get('start_index', 'N/A')} - {citation.get('end_index', 'N/A')}")
                                    if citation.get("license"):
                                        st.write(f"- License: {citation['license']}")
                                    st.divider()
                        
                        st.session_state.messages.append(message_data)
                    else:
                        error_message = "Sorry, I couldn't process your question. Please try again."
                        if response and response.get("error"):
                            error_message = f"Error: {response['error']}"
                        
                        st.error(error_message)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_message
                        })
    
    with col2:
        st.header("ℹ️ Information")
        
        with st.container():
            st.subheader("📊 Statistics")
            st.metric("Uploaded Files", len(st.session_state.uploaded_files))
            st.metric("Chat Messages", len(st.session_state.messages))
        
        with st.container():
            st.subheader("🔧 Features")
            st.write("✅ Multi-format support")
            st.write("✅ AI-powered search")
            st.write("✅ Citation tracking")
            st.write("✅ Chat history")
            st.write("✅ File management")
        
        with st.container():
            st.subheader("💡 Tips")
            st.write("• Ask specific questions")
            st.write("• Reference specific topics")
            st.write("• Use follow-up questions")
            st.write("• Check citations for sources")


if __name__ == "__main__":
    main()