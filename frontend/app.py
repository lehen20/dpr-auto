import streamlit as st
import requests
import json
from typing import Optional, List, Dict
import os
from datetime import datetime

# BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BACKEND_URL = "http://localhost:8000"


def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []
    if "current_store" not in st.session_state:
        st.session_state.current_store = None
    if "available_stores" not in st.session_state:
        st.session_state.available_stores = []


def get_available_stores() -> List[Dict]:
    """Get list of available file search stores."""
    try:
        response = requests.get(f"{BACKEND_URL}/stores", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("stores", [])
        return []
    except:
        return []


def initialize_predefined_stores():
    """Initialize the predefined stores."""
    try:
        response = requests.post(f"{BACKEND_URL}/initialize_stores", timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"success": False}
    except:
        return {"success": False}


def upload_file(file, store_name: Optional[str] = None) -> Optional[dict]:
    try:
        files = {"file": (file.name, file, file.type)}
        data = {}
        if store_name:
            data["store_name"] = store_name
            
        response = requests.post(f"{BACKEND_URL}/upload", files=files, data=data, timeout=300)
        
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


def query_documents(query: str, store_name: Optional[str] = None) -> Optional[dict]:
    try:
        payload = {"query": query}
        if store_name:
            payload["file_search_store_name"] = store_name
            
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


def extract_data(store_name: str, extraction_type: str) -> Optional[dict]:
    """Extract structured data from a file search store."""
    try:
        payload = {
            "store_name": store_name,
            "extraction_type": extraction_type
        }
        response = requests.post(
            f"{BACKEND_URL}/extract_data",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Data extraction failed: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during extraction: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during extraction: {str(e)}")
        return None


def check_backend_health() -> bool:
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def document_search_tab():
    """Tab for document upload and search."""
    st.header("📚 Document Search")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📁 File Management")
        
        # Store selection
        if st.session_state.available_stores:
            store_options = ["Create New Store"] + [s["display_name"] for s in st.session_state.available_stores]
            selected_store_option = st.selectbox(
                "Select File Search Store:",
                store_options,
                help="Choose which store to upload files to"
            )
            
            if selected_store_option == "Create New Store":
                new_store_name = st.text_input("Enter new store name:")
                if new_store_name:
                    selected_store = new_store_name
                else:
                    selected_store = None
            else:
                # Find the store name from display name
                selected_store = None
                for store in st.session_state.available_stores:
                    if store["display_name"] == selected_store_option:
                        selected_store = store["name"]
                        break
        else:
            selected_store = None
            st.warning("No stores available. Initialize stores first.")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a document",
            type=["pdf", "txt", "doc", "docx", "xls", "xlsx", "ppt", "pptx", 
                  "json", "csv", "xml", "html", "md", "rtf"],
            help="Supported formats: PDF, Word, Excel, PowerPoint, Text files, and more (Max: 100MB)"
        )
        
        if uploaded_file is not None and selected_store:
            if st.button("Upload File"):
                with st.spinner("Uploading and indexing document..."):
                    result = upload_file(uploaded_file, selected_store)
                    
                    if result and result.get("success"):
                        st.success(f"✅ {result['filename']} uploaded successfully!")
                        st.session_state.uploaded_files.append({
                            "filename": result["filename"],
                            "file_id": result["file_id"],
                            "store_name": result.get("store_name", selected_store),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.rerun()
        
        # Current store indicator
        if st.session_state.current_store:
            st.info(f"🎯 Current Query Store: {st.session_state.current_store}")
        
        # Store selection for queries
        if st.session_state.available_stores:
            query_store_options = ["All Stores"] + [s["display_name"] for s in st.session_state.available_stores]
            selected_query_store = st.selectbox(
                "Query from store:",
                query_store_options,
                help="Select which store to query"
            )
            
            if selected_query_store != "All Stores":
                for store in st.session_state.available_stores:
                    if store["display_name"] == selected_query_store:
                        st.session_state.current_store = store["name"]
                        break
            else:
                st.session_state.current_store = None
        
        # Uploaded files list
        if st.session_state.uploaded_files:
            st.subheader("📋 Uploaded Files")
            for i, file_info in enumerate(st.session_state.uploaded_files):
                with st.expander(f"{file_info['filename']}", expanded=False):
                    st.write(f"**File ID:** {file_info['file_id'][:8]}...")
                    st.write(f"**Store:** {file_info.get('store_name', 'Unknown')}")
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
    
    with col2:
        st.subheader("💬 Chat Interface")
        
        if not st.session_state.uploaded_files:
            st.info("👆 Please upload a document first to start asking questions.")
        
        # Display chat messages
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
        
        # Chat input
        if prompt := st.chat_input("Ask a question about your documents...", disabled=not st.session_state.uploaded_files):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = query_documents(prompt, st.session_state.current_store)
                    
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


def data_extraction_tab():
    """Tab for structured data extraction."""
    st.header("🔍 Data Extraction")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Extract Information")
        
        # Store selection
        if st.session_state.available_stores:
            store_options = [s["display_name"] for s in st.session_state.available_stores]
            selected_store_display = st.selectbox(
                "Select Store for Extraction:",
                store_options,
                help="Choose which store to extract data from"
            )
            
            selected_store_name = None
            for store in st.session_state.available_stores:
                if store["display_name"] == selected_store_display:
                    selected_store_name = store["name"]
                    break
        else:
            st.warning("No stores available. Upload documents first.")
            return
        
        # Extraction type selection
        extraction_types = {
            "Certificate of Incorporation": "certificate_of_incorporation",
            "MoA AoA": "moa_aoa", 
            "Machine Quotation": "machine_quotation"
        }
        
        selected_extraction_display = st.selectbox(
            "Select Extraction Type:",
            list(extraction_types.keys()),
            help="Choose what type of information to extract"
        )
        
        extraction_type = extraction_types[selected_extraction_display]
        
        if st.button("🚀 Extract Data", disabled=not selected_store_name):
            with st.spinner("Extracting structured data..."):
                result = extract_data(selected_store_name, extraction_type)
                
                if result and result.get("success"):
                    st.session_state[f"extracted_data_{extraction_type}"] = result["data"]
                    st.success("✅ Data extraction completed!")
                else:
                    st.error(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
    
    with col2:
        st.subheader("📋 Extracted Data")
        
        # Display extracted data based on type
        if extraction_type == "certificate_of_incorporation":
            data_key = f"extracted_data_{extraction_type}"
            if data_key in st.session_state:
                data = st.session_state[data_key]
                
                st.markdown("### Certificate of Incorporation")
                
                # Display editable fields
                fields = [
                    ("Company Name", "company_name"),
                    ("Registration Number", "registration_number"),
                    ("Company Type", "company_type"),
                    ("Date of Formation", "date_of_formation"),
                    ("Date of Commencement", "date_of_commencement"),
                    ("Registered Office Address", "registered_office_address")
                ]
                
                # Edit mode toggle
                edit_mode = st.checkbox("✏️ Edit Mode", key="edit_cert")
                
                edited_data = data.copy()
                for label, key in fields:
                    value = data.get(key, "")
                    if edit_mode:
                        new_value = st.text_input(label, value=value if value else "", key=f"cert_{key}")
                        edited_data[key] = new_value
                    else:
                        display_value = value if value else "Not found"
                        st.text_input(label, value=display_value, disabled=True)
                
                # Update data if in edit mode
                if edit_mode:
                    st.session_state[data_key] = edited_data
                
                # Download as JSON
                if st.button("📥 Download as JSON"):
                    json_str = json.dumps(data, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"certificate_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            else:
                st.info("👆 Extract data first to see results here.")
        
        elif extraction_type == "moa_aoa":
            data_key = f"extracted_data_{extraction_type}"
            if data_key in st.session_state:
                data = st.session_state[data_key]
                
                st.markdown("### MoA & AoA Data")
                
                # MoA/AoA Present indicator
                moa_present = data.get("moa_aoa_present", None)
                if moa_present is not None:
                    status_color = "🟢" if moa_present else "🔴"
                    st.markdown(f"{status_color} **MoA/AoA Present:** {'Yes' if moa_present else 'No'}")
                else:
                    st.markdown("🔶 **MoA/AoA Present:** Unknown")
                
                st.divider()
                
                # Authorized Share Capital
                st.markdown("#### 💰 Authorized Share Capital")
                share_capital = data.get("authorized_share_capital")
                if share_capital:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Value", value=str(share_capital.get("value", "Not found")), disabled=True)
                    with col2:
                        st.text_input("Unit", value=share_capital.get("unit", "INR"), disabled=True)
                    if share_capital.get("raw_text"):
                        st.text_area("Raw Text", value=share_capital.get("raw_text"), disabled=True, height=60)
                else:
                    st.info("No share capital information found")
                
                st.divider()
                
                # Main Objectives
                st.markdown("#### 🎯 Main Objectives")
                main_obj_raw = data.get("main_objectives_raw")
                if main_obj_raw:
                    st.text_area("Raw Clause", value=main_obj_raw, disabled=True, height=100)
                
                main_obj_summary = data.get("main_objectives_summary")
                if main_obj_summary:
                    st.text_area("Summary (DPR-style)", value=main_obj_summary, disabled=True, height=60)
                
                if not main_obj_raw and not main_obj_summary:
                    st.info("No main objectives found")
                
                st.divider()
                
                # Inclusiveness Policy
                st.markdown("#### 🤝 Inclusiveness/Membership Policy")
                incl_raw = data.get("inclusiveness_policy_raw")
                if incl_raw:
                    st.text_area("Raw Clause", value=incl_raw, disabled=True, height=100)
                
                incl_summary = data.get("inclusiveness_policy_summary")
                if incl_summary:
                    st.text_area("Summary (DPR-style)", value=incl_summary, disabled=True, height=60)
                
                if not incl_raw and not incl_summary:
                    st.info("No inclusiveness policy found")
                
                st.divider()
                
                # Board List
                st.markdown("#### 👥 Board of Directors")
                board_list = data.get("board_list")
                if board_list and isinstance(board_list, list):
                    for i, member in enumerate(board_list):
                        with st.expander(f"Board Member {i+1}: {member.get('name', 'Unknown')}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.text_input("Name", value=member.get("name", "Not found"), disabled=True, key=f"board_name_{i}")
                            with col2:
                                st.text_input("Role", value=member.get("role", "Not found"), disabled=True, key=f"board_role_{i}")
                            if member.get("raw_text"):
                                st.text_area("Raw Text", value=member.get("raw_text"), disabled=True, height=60, key=f"board_raw_{i}")
                else:
                    st.info("No board members found")
                
                st.divider()
                
                # Shareholding Schedule
                st.markdown("#### 📊 Shareholding Schedule")
                shareholding = data.get("shareholding_schedule")
                if shareholding and isinstance(shareholding, list):
                    for i, shareholder in enumerate(shareholding):
                        with st.expander(f"Shareholder {i+1}: {shareholder.get('shareholder', 'Unknown')}"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.text_input("Shareholder", value=shareholder.get("shareholder", "Not found"), disabled=True, key=f"sh_name_{i}")
                            with col2:
                                st.text_input("Shares", value=str(shareholder.get("shares", "Not found")), disabled=True, key=f"sh_shares_{i}")
                            with col3:
                                st.text_input("Percentage", value=f"{shareholder.get('percentage', 'Not found')}%", disabled=True, key=f"sh_pct_{i}")
                else:
                    st.info("No shareholding schedule found")
                
                st.divider()
                
                # Download as JSON
                if st.button("📥 Download as JSON", key="download_moa"):
                    json_str = json.dumps(data, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name=f"moa_aoa_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            else:
                st.info("👆 Extract data first to see results here.")
        
        else:
            st.info(f"Data extraction for {selected_extraction_display} will be available soon.")


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
    
    # Sidebar for store management
    with st.sidebar:
        st.header("🏪 Store Management")
        
        if st.button("🔄 Refresh Stores"):
            st.session_state.available_stores = get_available_stores()
        
        if st.button("⚡ Initialize Predefined Stores"):
            with st.spinner("Initializing stores..."):
                result = initialize_predefined_stores()
                if result.get("success"):
                    st.success("✅ Stores initialized!")
                    st.session_state.available_stores = get_available_stores()
                else:
                    st.error("❌ Failed to initialize stores")
        
        # Load stores if not already loaded
        if not st.session_state.available_stores:
            st.session_state.available_stores = get_available_stores()
        
        if st.session_state.available_stores:
            st.subheader("📋 Available Stores")
            for store in st.session_state.available_stores:
                st.write(f"• {store['display_name']}")
        else:
            st.info("No stores found. Initialize stores to get started.")
        
        st.divider()
        st.subheader("ℹ️ Information")
        st.metric("Available Stores", len(st.session_state.available_stores))
        st.metric("Uploaded Files", len(st.session_state.uploaded_files))
        st.metric("Chat Messages", len(st.session_state.messages))
    
    # Main tabs
    tab1, tab2 = st.tabs(["🔍 Document Search", "📊 Data Extraction"])
    
    with tab1:
        document_search_tab()
    
    with tab2:
        data_extraction_tab()


if __name__ == "__main__":
    main()