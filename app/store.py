import os
import json
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime
import fcntl


class JSONFileStore:
    """Simple JSON file store with atomic writes and basic error handling"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = base_path
        self.docs_path = os.path.join(base_path, "docs")
        self.projects_path = os.path.join(base_path, "projects")
        
        # Ensure directories exist
        os.makedirs(self.docs_path, exist_ok=True)
        os.makedirs(self.projects_path, exist_ok=True)
    
    def _get_doc_metadata_path(self, doc_id: str) -> str:
        """Get path for document metadata file"""
        return os.path.join(self.docs_path, f"{doc_id}_metadata.json")
    
    def _get_project_path(self, project_id: str) -> str:
        """Get path for project DPR file"""
        return os.path.join(self.projects_path, f"{project_id}.json")
    
    def _atomic_write(self, file_path: str, data: Dict[str, Any]) -> bool:
        """Write data to file atomically using temp file + rename"""
        try:
            # Create temporary file in same directory
            temp_dir = os.path.dirname(file_path)
            with tempfile.NamedTemporaryFile(
                mode='w', 
                dir=temp_dir, 
                delete=False, 
                suffix='.tmp'
            ) as temp_file:
                # Write data to temp file
                json.dump(data, temp_file, indent=2, default=str)
                temp_file.flush()
                os.fsync(temp_file.fileno())  # Force write to disk
                temp_path = temp_file.name
            
            # Atomic rename
            shutil.move(temp_path, file_path)
            return True
            
        except Exception as e:
            # Cleanup temp file if it exists
            try:
                if 'temp_path' in locals():
                    os.unlink(temp_path)
            except:
                pass
            print(f"Atomic write failed: {e}")
            return False
    
    def _read_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Read JSON data from file with error handling"""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r') as f:
                # Use file locking for read consistency
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except (json.JSONDecodeError, IOError) as e:
            print(f"Failed to read file {file_path}: {e}")
            return None
    
    def save_doc(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """Save document metadata"""
        # Add timestamp
        metadata['last_updated'] = datetime.now().isoformat()
        metadata['doc_id'] = doc_id
        
        file_path = self._get_doc_metadata_path(doc_id)
        return self._atomic_write(file_path, metadata)
    
    def load_doc(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load document metadata"""
        file_path = self._get_doc_metadata_path(doc_id)
        return self._read_json_file(file_path)
    
    def delete_doc(self, doc_id: str) -> bool:
        """Delete document and its metadata"""
        try:
            # Delete metadata file
            metadata_path = self._get_doc_metadata_path(doc_id)
            if os.path.exists(metadata_path):
                os.unlink(metadata_path)
            
            # Delete PDF file if it exists
            pdf_path = os.path.join(self.docs_path, f"{doc_id}.pdf")
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
            
            return True
            
        except Exception as e:
            print(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def list_docs(self) -> List[Dict[str, Any]]:
        """List all documents with their metadata"""
        docs = []
        try:
            for filename in os.listdir(self.docs_path):
                if filename.endswith('_metadata.json'):
                    doc_id = filename.replace('_metadata.json', '')
                    metadata = self.load_doc(doc_id)
                    if metadata:
                        docs.append(metadata)
        except Exception as e:
            print(f"Failed to list documents: {e}")
        
        return docs
    
    def save_project(self, project_id: str, dpr_data: Dict[str, Any]) -> bool:
        """Save project DPR data"""
        # Add timestamp and project ID
        dpr_data['last_updated'] = datetime.now().isoformat()
        dpr_data['project_id'] = project_id
        
        file_path = self._get_project_path(project_id)
        
        # Create backup if file exists
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            try:
                shutil.copy2(file_path, backup_path)
            except Exception as e:
                print(f"Failed to create backup: {e}")
        
        return self._atomic_write(file_path, dpr_data)
    
    def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load project DPR data"""
        file_path = self._get_project_path(project_id)
        return self._read_json_file(file_path)
    
    def delete_project(self, project_id: str) -> bool:
        """Delete project and its backup"""
        try:
            # Delete main file
            project_path = self._get_project_path(project_id)
            if os.path.exists(project_path):
                os.unlink(project_path)
            
            # Delete backup if it exists
            backup_path = f"{project_path}.backup"
            if os.path.exists(backup_path):
                os.unlink(backup_path)
            
            return True
            
        except Exception as e:
            print(f"Failed to delete project {project_id}: {e}")
            return False
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects with their basic info"""
        projects = []
        try:
            for filename in os.listdir(self.projects_path):
                if filename.endswith('.json') and not filename.endswith('.backup'):
                    project_id = filename.replace('.json', '')
                    project_data = self.load_project(project_id)
                    if project_data:
                        # Return summary info only
                        summary = {
                            'project_id': project_id,
                            'last_updated': project_data.get('last_updated'),
                            'extraction_time': project_data.get('extraction_time'),
                            'document_count': len(project_data.get('documents', [])),
                            'spv_name': None
                        }
                        
                        # Extract SPV name if available
                        spv = project_data.get('spv', {})
                        if spv.get('name') and spv['name'].get('value'):
                            summary['spv_name'] = spv['name']['value']
                        
                        projects.append(summary)
                        
        except Exception as e:
            print(f"Failed to list projects: {e}")
        
        return projects
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            docs_count = len([f for f in os.listdir(self.docs_path) if f.endswith('_metadata.json')])
            projects_count = len([f for f in os.listdir(self.projects_path) if f.endswith('.json') and not f.endswith('.backup')])
            
            # Calculate total storage size
            total_size = 0
            for root, dirs, files in os.walk(self.base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
            
            return {
                'documents_count': docs_count,
                'projects_count': projects_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'base_path': self.base_path
            }
            
        except Exception as e:
            print(f"Failed to get storage stats: {e}")
            return {
                'documents_count': 0,
                'projects_count': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0.0,
                'base_path': self.base_path,
                'error': str(e)
            }
    
    def cleanup_old_files(self, days_old: int = 30) -> Dict[str, int]:
        """Cleanup files older than specified days"""
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
        
        cleaned_docs = 0
        cleaned_projects = 0
        
        try:
            # Cleanup old documents
            for filename in os.listdir(self.docs_path):
                file_path = os.path.join(self.docs_path, filename)
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.unlink(file_path)
                        cleaned_docs += 1
                    except:
                        pass
            
            # Cleanup old project backups
            for filename in os.listdir(self.projects_path):
                if filename.endswith('.backup'):
                    file_path = os.path.join(self.projects_path, filename)
                    if os.path.getmtime(file_path) < cutoff_time:
                        try:
                            os.unlink(file_path)
                            cleaned_projects += 1
                        except:
                            pass
                            
        except Exception as e:
            print(f"Cleanup failed: {e}")
        
        return {
            'cleaned_documents': cleaned_docs,
            'cleaned_project_backups': cleaned_projects
        }


# Global store instance
_store_instance = None

def get_store() -> JSONFileStore:
    """Get the global store instance"""
    global _store_instance
    if _store_instance is None:
        _store_instance = JSONFileStore()
    return _store_instance

# Convenience functions for backward compatibility
def save_doc(doc_id: str, metadata: Dict[str, Any]) -> bool:
    """Save document metadata"""
    return get_store().save_doc(doc_id, metadata)

def load_doc(doc_id: str) -> Optional[Dict[str, Any]]:
    """Load document metadata"""
    return get_store().load_doc(doc_id)

def save_project(project_id: str, dpr_data: Dict[str, Any]) -> bool:
    """Save project DPR data"""
    return get_store().save_project(project_id, dpr_data)

def load_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Load project DPR data"""
    return get_store().load_project(project_id)


if __name__ == "__main__":
    # Test the store functionality
    print("Testing JSONFileStore...")
    
    store = JSONFileStore("./test_data")
    
    # Test document operations
    test_doc_metadata = {
        "filename": "test.pdf",
        "file_path": "./test.pdf",
        "pages": 5,
        "upload_time": datetime.now().isoformat()
    }
    
    print("Testing document save/load...")
    assert store.save_doc("test_doc_1", test_doc_metadata), "Document save failed"
    loaded_doc = store.load_doc("test_doc_1")
    assert loaded_doc is not None, "Document load failed"
    assert loaded_doc["filename"] == "test.pdf", "Document data mismatch"
    print("✓ Document operations working")
    
    # Test project operations
    test_project_data = {
        "extraction_time": datetime.now().isoformat(),
        "documents": ["test_doc_1"],
        "spv": {
            "name": {"value": "Test Company Ltd", "confidence": 0.9}
        }
    }
    
    print("Testing project save/load...")
    assert store.save_project("test_project_1", test_project_data), "Project save failed"
    loaded_project = store.load_project("test_project_1")
    assert loaded_project is not None, "Project load failed"
    assert loaded_project["spv"]["name"]["value"] == "Test Company Ltd", "Project data mismatch"
    print("✓ Project operations working")
    
    # Test listing
    print("Testing list operations...")
    docs = store.list_docs()
    projects = store.list_projects()
    assert len(docs) >= 1, "Document listing failed"
    assert len(projects) >= 1, "Project listing failed"
    print("✓ List operations working")
    
    # Test stats
    print("Testing storage stats...")
    stats = store.get_storage_stats()
    assert stats["documents_count"] >= 1, "Stats failed"
    print(f"✓ Storage stats: {stats}")
    
    # Cleanup test files
    store.delete_doc("test_doc_1")
    store.delete_project("test_project_1")
    
    print("All tests passed!")