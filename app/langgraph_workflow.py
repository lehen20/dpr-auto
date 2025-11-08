# LangGraph Workflow Description for DPR Automation Pipeline
# This file defines the workflow graph structure for processing documents

workflow_graph = {
    "name": "dpr_automation_workflow",
    "description": "End-to-end workflow for processing CoI and MoA/AoA documents into DPR format",
    "version": "1.0",
    "nodes": [
        {
            "id": "ocr_layout",
            "name": "OCR and Layout Analysis",
            "type": "processor",
            "purpose": "Extract text segments and layout information from PDF documents",
            "implementation": "app.extractors.ocr_and_layout",
            "inputs": {
                "file_path": "string",
                "doc_id": "string"
            },
            "outputs": {
                "segments": "List[Segment]",
                "page_count": "int",
                "processing_status": "string"
            },
            "retry_policy": {
                "max_retries": 3,
                "retry_delay": 2,
                "retry_on": ["OCRError", "FileAccessError"]
            },
            "cache_strategy": {
                "enabled": True,
                "ttl_hours": 24,
                "cache_key": "file_hash"
            },
            "timeout_seconds": 120,
            "dependencies": [],
            "error_handling": "fallback_to_pytesseract"
        },
        {
            "id": "doc_classifier",
            "name": "Document Type Classifier",
            "type": "classifier",
            "purpose": "Classify document type (CoI, MoA/AoA, or unknown) based on content analysis",
            "implementation": "app.extractors.detect_doc_type",
            "inputs": {
                "segments": "List[Segment]"
            },
            "outputs": {
                "doc_type": "string",
                "confidence": "float",
                "classification_features": "dict"
            },
            "retry_policy": {
                "max_retries": 2,
                "retry_delay": 1,
                "retry_on": ["ClassificationError"]
            },
            "cache_strategy": {
                "enabled": True,
                "ttl_hours": 12,
                "cache_key": "segments_hash"
            },
            "timeout_seconds": 30,
            "dependencies": ["ocr_layout"],
            "error_handling": "return_unknown_type"
        },
        {
            "id": "table_extractor",
            "name": "Table Structure Extractor",
            "type": "extractor",
            "purpose": "Extract and parse tabular data from documents (shareholding, board info)",
            "implementation": "app.extractors.find_table_by_header",
            "inputs": {
                "segments": "List[Segment]",
                "header_keywords": "List[string]"
            },
            "outputs": {
                "tables": "List[dict]",
                "table_locations": "List[dict]"
            },
            "retry_policy": {
                "max_retries": 2,
                "retry_delay": 1,
                "retry_on": ["TableParsingError"]
            },
            "cache_strategy": {
                "enabled": False
            },
            "timeout_seconds": 45,
            "dependencies": ["ocr_layout"],
            "error_handling": "skip_malformed_tables"
        },
        {
            "id": "regex_field_extractor",
            "name": "Regex Field Extractor",
            "type": "extractor",
            "purpose": "Extract structured fields using regex patterns (CIN, dates, amounts)",
            "implementation": "app.extractors.extract_incorporation_fields",
            "inputs": {
                "segments": "List[Segment]",
                "doc_id": "string",
                "doc_type": "string"
            },
            "outputs": {
                "extracted_fields": "Dict[string, ExtractionField]",
                "extraction_metadata": "dict"
            },
            "retry_policy": {
                "max_retries": 1,
                "retry_delay": 1,
                "retry_on": ["RegexError"]
            },
            "cache_strategy": {
                "enabled": True,
                "ttl_hours": 6,
                "cache_key": "doc_id_type"
            },
            "timeout_seconds": 60,
            "dependencies": ["doc_classifier"],
            "error_handling": "partial_extraction_allowed",
            "conditional_execution": {
                "condition": "doc_type in ['certificate_of_incorporation', 'moa_aoa']",
                "skip_if_false": False
            }
        },
        {
            "id": "llm_summarizer",
            "name": "LLM-based Summarizer",
            "type": "summarizer",
            "purpose": "Generate summaries for complex clauses using Gemini LLM",
            "implementation": "app.gemini_prompts.summarize_clause",
            "inputs": {
                "raw_clauses": "List[string]",
                "context": "dict"
            },
            "outputs": {
                "summaries": "List[dict]",
                "purpose_tags": "List[List[string]]"
            },
            "retry_policy": {
                "max_retries": 3,
                "retry_delay": 5,
                "retry_on": ["APIError", "RateLimitError"]
            },
            "cache_strategy": {
                "enabled": True,
                "ttl_hours": 48,
                "cache_key": "clause_hash"
            },
            "timeout_seconds": 90,
            "dependencies": ["regex_field_extractor"],
            "error_handling": "use_fallback_summary",
            "conditional_execution": {
                "condition": "len(raw_clauses) > 0 and confidence < 0.8",
                "skip_if_false": True
            }
        },
        {
            "id": "merger",
            "name": "Field Merger and Consolidator",
            "type": "consolidator",
            "purpose": "Merge extracted fields from multiple documents into unified DPR structure",
            "implementation": "app.main.merge_extractions",
            "inputs": {
                "extraction_results": "List[ExtractionResult]",
                "project_id": "string"
            },
            "outputs": {
                "merged_dpr": "DPR",
                "merge_conflicts": "List[dict]",
                "confidence_scores": "dict"
            },
            "retry_policy": {
                "max_retries": 2,
                "retry_delay": 2,
                "retry_on": ["MergeError"]
            },
            "cache_strategy": {
                "enabled": False
            },
            "timeout_seconds": 30,
            "dependencies": ["regex_field_extractor", "llm_summarizer"],
            "error_handling": "preserve_highest_confidence",
            "merge_strategies": {
                "conflict_resolution": "highest_confidence",
                "duplicate_handling": "combine_source_refs",
                "missing_field_policy": "mark_for_review"
            }
        },
        {
            "id": "validator",
            "name": "Data Validator and Quality Checker",
            "type": "validator",
            "purpose": "Validate extracted data quality and flag fields needing human review",
            "implementation": "app.validators.validate_dpr_fields",
            "inputs": {
                "dpr_data": "DPR",
                "validation_rules": "dict"
            },
            "outputs": {
                "validation_result": "dict",
                "flagged_fields": "List[string]",
                "warnings": "List[string]"
            },
            "retry_policy": {
                "max_retries": 1,
                "retry_delay": 1,
                "retry_on": ["ValidationError"]
            },
            "cache_strategy": {
                "enabled": False
            },
            "timeout_seconds": 20,
            "dependencies": ["merger"],
            "error_handling": "log_validation_failures",
            "validation_rules": {
                "mandatory_fields": ["spv.name", "spv.registration_number"],
                "confidence_threshold": 0.85,
                "format_validators": {
                    "cin": "^[UL]\\d{5}[A-Z]{2}\\d{4}[A-Z]{3}\\d{6}$",
                    "date": "^\\d{4}-\\d{2}-\\d{2}$"
                }
            }
        },
        {
            "id": "store",
            "name": "Data Store Manager",
            "type": "storage",
            "purpose": "Persist processed data and maintain document relationships",
            "implementation": "app.store.save_project",
            "inputs": {
                "dpr_data": "DPR",
                "project_id": "string",
                "metadata": "dict"
            },
            "outputs": {
                "storage_result": "dict",
                "file_paths": "List[string]"
            },
            "retry_policy": {
                "max_retries": 3,
                "retry_delay": 2,
                "retry_on": ["IOError", "StorageError"]
            },
            "cache_strategy": {
                "enabled": False
            },
            "timeout_seconds": 15,
            "dependencies": ["validator"],
            "error_handling": "atomic_write_with_backup",
            "storage_config": {
                "format": "json",
                "backup_enabled": True,
                "compression": False,
                "versioning": True
            }
        }
    ],
    "edges": [
        {
            "from": "ocr_layout",
            "to": "doc_classifier",
            "condition": "success",
            "data_mapping": {
                "segments": "segments"
            }
        },
        {
            "from": "doc_classifier",
            "to": "table_extractor",
            "condition": "doc_type != 'unknown'",
            "data_mapping": {
                "segments": "segments"
            }
        },
        {
            "from": "doc_classifier",
            "to": "regex_field_extractor",
            "condition": "doc_type in ['certificate_of_incorporation', 'moa_aoa']",
            "data_mapping": {
                "segments": "segments",
                "doc_type": "doc_type"
            }
        },
        {
            "from": "regex_field_extractor",
            "to": "llm_summarizer",
            "condition": "any(field.confidence < 0.8 for field in extracted_fields.values())",
            "data_mapping": {
                "extracted_fields": "raw_clauses"
            }
        },
        {
            "from": "regex_field_extractor",
            "to": "merger",
            "condition": "always",
            "data_mapping": {
                "extracted_fields": "extraction_results"
            }
        },
        {
            "from": "table_extractor",
            "to": "merger",
            "condition": "len(tables) > 0",
            "data_mapping": {
                "tables": "table_data"
            }
        },
        {
            "from": "llm_summarizer",
            "to": "merger",
            "condition": "summaries_generated",
            "data_mapping": {
                "summaries": "llm_enhancements"
            }
        },
        {
            "from": "merger",
            "to": "validator",
            "condition": "merge_successful",
            "data_mapping": {
                "merged_dpr": "dpr_data"
            }
        },
        {
            "from": "validator",
            "to": "store",
            "condition": "validation_passed or allow_partial_save",
            "data_mapping": {
                "dpr_data": "dpr_data",
                "validation_result": "metadata"
            }
        }
    ],
    "execution_config": {
        "parallel_execution": {
            "enabled": True,
            "max_parallel_nodes": 3,
            "parallelizable_stages": [
                ["table_extractor", "regex_field_extractor"]
            ]
        },
        "error_handling": {
            "strategy": "partial_success",
            "fail_fast": False,
            "rollback_on_critical_failure": True,
            "critical_nodes": ["ocr_layout", "store"]
        },
        "monitoring": {
            "metrics_collection": True,
            "performance_tracking": True,
            "error_logging": True,
            "execution_tracing": True
        },
        "resource_limits": {
            "max_execution_time_minutes": 30,
            "max_memory_mb": 2048,
            "max_file_size_mb": 100
        }
    },
    "state_management": {
        "state_persistence": True,
        "checkpoint_nodes": ["merger", "validator"],
        "resume_capability": True,
        "state_cleanup_after_hours": 24
    },
    "input_schema": {
        "file_path": "string",
        "doc_id": "string",
        "project_id": "string",
        "processing_options": {
            "ocr_language": "string",
            "quality_threshold": "float",
            "enable_llm_enhancement": "boolean"
        }
    },
    "output_schema": {
        "processed_dpr": "DPR",
        "execution_summary": {
            "nodes_executed": "List[string]",
            "execution_time_seconds": "float",
            "errors": "List[dict]",
            "warnings": "List[dict]"
        },
        "artifacts": {
            "extracted_segments": "List[Segment]",
            "intermediate_results": "dict",
            "validation_report": "dict"
        }
    }
}

# Workflow execution functions
def get_workflow_definition():
    """Return the complete workflow definition"""
    return workflow_graph

def get_node_by_id(node_id: str):
    """Get a specific node definition by ID"""
    for node in workflow_graph["nodes"]:
        if node["id"] == node_id:
            return node
    return None

def get_execution_order():
    """Calculate optimal execution order based on dependencies"""
    nodes = workflow_graph["nodes"]
    edges = workflow_graph["edges"]
    
    # Simple topological sort for execution order
    execution_order = []
    remaining_nodes = {node["id"]: node for node in nodes}
    
    while remaining_nodes:
        # Find nodes with no unmet dependencies
        ready_nodes = []
        for node_id, node in remaining_nodes.items():
            dependencies = node.get("dependencies", [])
            if all(dep not in remaining_nodes for dep in dependencies):
                ready_nodes.append(node_id)
        
        if not ready_nodes:
            # Circular dependency or error
            break
            
        # Add ready nodes to execution order
        for node_id in ready_nodes:
            execution_order.append(node_id)
            del remaining_nodes[node_id]
    
    return execution_order

def validate_workflow():
    """Validate workflow definition for consistency"""
    issues = []
    
    # Check for missing node implementations
    for node in workflow_graph["nodes"]:
        implementation = node.get("implementation")
        if implementation and not implementation.startswith("app."):
            issues.append(f"Invalid implementation path for node {node['id']}: {implementation}")
    
    # Check edge references
    node_ids = {node["id"] for node in workflow_graph["nodes"]}
    for edge in workflow_graph["edges"]:
        if edge["from"] not in node_ids:
            issues.append(f"Edge references unknown source node: {edge['from']}")
        if edge["to"] not in node_ids:
            issues.append(f"Edge references unknown target node: {edge['to']}")
    
    return issues

# Export workflow for external systems
def export_workflow_json():
    """Export workflow as JSON string"""
    import json
    return json.dumps(workflow_graph, indent=2)

def export_workflow_yaml():
    """Export workflow as YAML string"""
    try:
        import yaml
        return yaml.dump(workflow_graph, default_flow_style=False, indent=2)
    except ImportError:
        return "YAML library not available"

if __name__ == "__main__":
    print("DPR Automation Workflow Definition")
    print("==================================")
    print(f"Workflow: {workflow_graph['name']}")
    print(f"Version: {workflow_graph['version']}")
    print(f"Nodes: {len(workflow_graph['nodes'])}")
    print(f"Edges: {len(workflow_graph['edges'])}")
    
    print("\nExecution Order:")
    for i, node_id in enumerate(get_execution_order(), 1):
        node = get_node_by_id(node_id)
        print(f"{i}. {node['name']} ({node_id})")
    
    print("\nValidation Issues:")
    issues = validate_workflow()
    if issues:
        for issue in issues:
            print(f"- {issue}")
    else:
        print("- No issues found")