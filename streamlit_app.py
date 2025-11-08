import streamlit as st
import requests
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List
import base64


# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="DPR Automation Tool",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize session state variables"""
    if 'uploaded_docs' not in st.session_state:
        st.session_state.uploaded_docs = []
    if 'current_project_id' not in st.session_state:
        st.session_state.current_project_id = str(uuid.uuid4())
    if 'extracted_fields' not in st.session_state:
        st.session_state.extracted_fields = {}
    if 'merged_dpr' not in st.session_state:
        st.session_state.merged_dpr = None

def api_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    """Make API request with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = requests.request(method, url, **kwargs)
        return response
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend API. Make sure the FastAPI server is running on port 8000.")
        st.stop()
    except Exception as e:
        st.error(f"❌ API request failed: {str(e)}")
        st.stop()

def upload_documents():
    """Handle document upload"""
    st.header("📤 Upload Documents")
    
    uploaded_files = st.file_uploader(
        "Choose PDF files (Certificate of Incorporation, MoA/AoA)",
        type="pdf",
        accept_multiple_files=True,
        help="Upload one or more PDF documents for processing"
    )
    
    if uploaded_files and st.button("Upload Files", type="primary"):
        with st.spinner("Uploading files..."):
            files = []
            for uploaded_file in uploaded_files:
                files.append(("files", (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")))
            
            response = api_request("POST", "/upload", files=files)
            
            if response.status_code == 200:
                uploaded_docs = response.json()
                st.session_state.uploaded_docs.extend(uploaded_docs)
                st.success(f"✅ Uploaded {len(uploaded_docs)} document(s) successfully!")
                
                # Display uploaded documents
                for doc in uploaded_docs:
                    st.info(f"📄 {doc['filename']} (ID: {doc['doc_id'][:8]}..., Pages: {doc['pages']})")
            else:
                st.error(f"❌ Upload failed: {response.text}")

def display_uploaded_documents():
    """Display uploaded documents with parse/extract options"""
    if not st.session_state.uploaded_docs:
        st.info("No documents uploaded yet. Please upload documents first.")
        return
    
    st.header("📋 Uploaded Documents")
    
    for doc in st.session_state.uploaded_docs:
        with st.expander(f"📄 {doc['filename']} ({doc['pages']} pages)"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"Parse", key=f"parse_{doc['doc_id']}"):
                    with st.spinner("Parsing document..."):
                        response = api_request("POST", f"/parse/{doc['doc_id']}")
                        
                        if response.status_code == 200:
                            parse_result = response.json()
                            st.success("✅ Document parsed successfully!")
                            
                            # Display segments
                            st.subheader("Text Segments")
                            for i, segment in enumerate(parse_result['segments'][:5]):  # Show first 5 segments
                                st.text_area(
                                    f"Segment {i+1} (Page {segment['page']}, {segment['segment_type']})",
                                    segment['text'][:200] + "..." if len(segment['text']) > 200 else segment['text'],
                                    height=100,
                                    key=f"segment_{doc['doc_id']}_{i}"
                                )
                        else:
                            st.error(f"❌ Parsing failed: {response.text}")
            
            with col2:
                if st.button(f"Extract Fields", key=f"extract_{doc['doc_id']}"):
                    with st.spinner("Extracting fields..."):
                        response = api_request("POST", f"/extract/{doc['doc_id']}")
                        
                        if response.status_code == 200:
                            extraction_result = response.json()
                            st.session_state.extracted_fields[doc['doc_id']] = extraction_result
                            st.success("✅ Fields extracted successfully!")
                            
                            # Display extracted fields
                            st.subheader("Extracted Fields")
                            for field_name, field_data in extraction_result['fields'].items():
                                confidence_color = "🟢" if field_data['confidence'] > 0.85 else "🟡" if field_data['confidence'] > 0.7 else "🔴"
                                st.write(f"{confidence_color} **{field_name}**: {field_data['value']} (Confidence: {field_data['confidence']:.2f})")
                        else:
                            st.error(f"❌ Extraction failed: {response.text}")
            
            with col3:
                if doc['doc_id'] in st.session_state.extracted_fields:
                    st.write("✅ Extracted")
                else:
                    st.write("⏳ Not extracted")

def edit_extracted_fields():
    """Allow human-in-the-loop editing of extracted fields"""
    if not st.session_state.extracted_fields:
        st.info("No extracted fields available. Please extract fields from documents first.")
        return
    
    st.header("✏️ Edit Extracted Fields")
    
    for doc_id, extraction_result in st.session_state.extracted_fields.items():
        st.subheader(f"Document: {doc_id[:8]}...")
        
        for field_name, field_data in extraction_result['fields'].items():
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    # Editable field value
                    current_value = field_data['value']
                    if isinstance(current_value, (dict, list)):
                        current_value = json.dumps(current_value, indent=2)
                    
                    new_value = st.text_area(
                        f"**{field_name}**",
                        value=str(current_value) if current_value is not None else "",
                        key=f"edit_{doc_id}_{field_name}",
                        height=100
                    )
                    
                    # Update if changed
                    if str(new_value) != str(current_value):
                        field_data['value'] = new_value
                        field_data['confidence'] = min(field_data['confidence'] + 0.1, 1.0)
                        field_data['needs_review'] = False
                
                with col2:
                    confidence = field_data['confidence']
                    confidence_color = "🟢" if confidence > 0.85 else "🟡" if confidence > 0.7 else "🔴"
                    st.metric("Confidence", f"{confidence:.2f}", delta=None)
                    st.write(confidence_color)
                
                with col3:
                    needs_review = field_data.get('needs_review', False)
                    if needs_review:
                        st.warning("⚠️ Needs Review")
                    else:
                        st.success("✅ Verified")
                
                # Show raw text source
                if field_data.get('raw_text'):
                    with st.expander("View source text"):
                        st.text(field_data['raw_text'][:300] + "..." if len(field_data['raw_text']) > 300 else field_data['raw_text'])

def merge_and_generate_dpr():
    """Merge fields and generate DPR draft"""
    if not st.session_state.extracted_fields:
        st.info("No extracted fields available. Please extract fields from documents first.")
        return
    
    st.header("🔄 Merge Fields & Generate DPR")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Merge Extracted Fields", type="primary"):
            with st.spinner("Merging fields from all documents..."):
                doc_ids = list(st.session_state.extracted_fields.keys())
                
                response = api_request(
                    "POST", 
                    f"/merge/{st.session_state.current_project_id}",
                    params={"doc_ids": doc_ids}
                )
                
                if response.status_code == 200:
                    merge_result = response.json()
                    st.session_state.merged_dpr = merge_result['merged_dpr']
                    st.success("✅ Fields merged successfully!")
                    
                    # Display extraction summary
                    summary = st.session_state.merged_dpr['extraction_summary']
                    st.subheader("Extraction Summary")
                    st.metric("Fields Extracted", summary['fields_extracted'])
                    
                    if summary['fields_missing']:
                        st.warning(f"Missing Fields: {', '.join(summary['fields_missing'])}")
                    
                    if summary['validation_warnings']:
                        st.warning("Validation Warnings:")
                        for warning in summary['validation_warnings']:
                            st.write(f"⚠️ {warning}")
                else:
                    st.error(f"❌ Merge failed: {response.text}")
    
    with col2:
        if st.session_state.merged_dpr and st.button("Generate DPR Draft", type="secondary"):
            with st.spinner("Generating DPR draft with Gemini..."):
                response = api_request("POST", f"/dpr/{st.session_state.current_project_id}/generate")
                
                if response.status_code == 200:
                    dpr_result = response.json()
                    st.success("✅ DPR draft generated successfully!")
                    
                    # Display generated sections
                    st.subheader("Generated DPR Sections")
                    for section in dpr_result['sections']:
                        with st.expander(f"📝 {section['title']}"):
                            st.write(section['body'])
                            if section['source_refs']:
                                st.caption(f"Sources: {', '.join(section['source_refs'])}")
                    
                    # Download options
                    st.subheader("Download Options")
                    st.download_button(
                        "📥 Download as Text",
                        data=dpr_result['dpr_text'],
                        file_name=f"dpr_draft_{st.session_state.current_project_id[:8]}.txt",
                        mime="text/plain"
                    )
                    
                    # JSON download
                    json_data = json.dumps(dpr_result, indent=2)
                    st.download_button(
                        "📥 Download as JSON",
                        data=json_data,
                        file_name=f"dpr_data_{st.session_state.current_project_id[:8]}.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"❌ DPR generation failed: {response.text}")

def display_merged_dpr():
    """Display the current merged DPR data"""
    if not st.session_state.merged_dpr:
        st.info("No merged DPR available. Please merge extracted fields first.")
        return
    
    st.header("📊 Merged DPR Data")
    
    dpr = st.session_state.merged_dpr
    
    # SPV Information
    st.subheader("🏢 SPV Information")
    spv = dpr.get('spv', {})
    
    for field_name, field_data in spv.items():
        if field_data and isinstance(field_data, dict) and 'value' in field_data:
            confidence = field_data.get('confidence', 0)
            confidence_color = "🟢" if confidence > 0.85 else "🟡" if confidence > 0.7 else "🔴"
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{field_name.replace('_', ' ').title()}**: {field_data['value']}")
            with col2:
                st.write(f"{confidence_color} {confidence:.2f}")
    
    # Extraction Summary
    st.subheader("📈 Extraction Summary")
    summary = dpr.get('extraction_summary', {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fields Extracted", summary.get('fields_extracted', 0))
    with col2:
        st.metric("Missing Fields", len(summary.get('fields_missing', [])))
    with col3:
        st.metric("Warnings", len(summary.get('validation_warnings', [])))
    
    # Document list
    st.subheader("📄 Source Documents")
    for doc_id in dpr.get('documents', []):
        st.write(f"• {doc_id}")

def main():
    """Main application"""
    init_session_state()
    
    # Sidebar
    st.sidebar.title("🤖 DPR Automation")
    st.sidebar.markdown("Transform CoI and MoA/AoA documents into DPR format using AI")
    
    # Project info
    st.sidebar.subheader("📁 Current Project")
    st.sidebar.write(f"ID: {st.session_state.current_project_id[:8]}...")
    
    if st.sidebar.button("🆕 New Project"):
        st.session_state.current_project_id = str(uuid.uuid4())
        st.session_state.uploaded_docs = []
        st.session_state.extracted_fields = {}
        st.session_state.merged_dpr = None
        st.experimental_rerun()
    
    # Navigation
    st.sidebar.subheader("📋 Navigation")
    page = st.sidebar.radio(
        "Choose a step:",
        [
            "📤 Upload Documents",
            "📋 Review Documents", 
            "✏️ Edit Fields",
            "🔄 Merge & Generate",
            "📊 View DPR"
        ]
    )
    
    # Progress indicator
    st.sidebar.subheader("📊 Progress")
    progress_steps = [
        ("Upload", len(st.session_state.uploaded_docs) > 0),
        ("Extract", len(st.session_state.extracted_fields) > 0),
        ("Merge", st.session_state.merged_dpr is not None),
    ]
    
    for step_name, completed in progress_steps:
        if completed:
            st.sidebar.write(f"✅ {step_name}")
        else:
            st.sidebar.write(f"⏳ {step_name}")
    
    # Main content
    st.title("🤖 DPR Automation Tool")
    st.markdown("**Transform Certificate of Incorporation and MoA/AoA documents into DPR format using AI**")
    
    # Route to appropriate page
    if page == "📤 Upload Documents":
        upload_documents()
    elif page == "📋 Review Documents":
        display_uploaded_documents()
    elif page == "✏️ Edit Fields":
        edit_extracted_fields()
    elif page == "🔄 Merge & Generate":
        merge_and_generate_dpr()
    elif page == "📊 View DPR":
        display_merged_dpr()
    
    # Footer
    st.markdown("---")
    st.markdown("**Built with ❤️ using Streamlit, FastAPI, and Gemini AI**")
    
    # API status check
    try:
        response = api_request("GET", "/health")
        if response.status_code == 200:
            st.sidebar.success("🟢 API Connected")
        else:
            st.sidebar.error("🔴 API Error")
    except:
        st.sidebar.error("🔴 API Disconnected")

if __name__ == "__main__":
    main()