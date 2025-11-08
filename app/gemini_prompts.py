import os
import json
import requests
from typing import Optional


# Template for clause summarization
clause_summarizer_prompt = """
You are a legal document analyzer. Summarize the following clause in exactly 40 words or less, focusing on the key business purpose and compliance requirements.

Raw clause text:
{raw_clause}

Return a JSON response with:
{
    "summary": "40-word summary here",
    "purpose_tags": ["tag1", "tag2", "tag3"]
}

Purpose tags should be from: ["compliance", "governance", "operations", "financial", "regulatory", "business_activity", "risk_management"]
"""

# Template for DPR synthesis
dpr_synthesis_prompt = """
You are a DPR (Detailed Project Report) writer for Indian corporate documentation. Generate professional DPR sections based on the extracted company information.

Company Information:
- SPV Name: {spv_name}
- Registration Number: {registration_number}
- Company Type: {company_type}
- Main Objectives: {main_objectives}

Generate the following DPR sections with proper formatting and inline source citations:

1. Proposal (Executive Summary)
2. Section 2.1: Introduction
3. Section 3: SPV Information
4. Section 7: Management Structure
5. Section 21: Conclusion

For each section, include:
- Professional business language
- Relevant details from the company information
- Source citations in format "(CoI p.1)" or "(MoA p.3)"
- Compliance with Indian corporate reporting standards

Return JSON format:
{
    "sections": [
        {
            "id": "proposal",
            "title": "Proposal",
            "body": "Section content with citations...",
            "source_refs": ["CoI p.1", "MoA p.2"]
        },
        // ... more sections
    ]
}
"""


def generate_text(prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> str:
    """
    Generate text using Gemini API
    
    Args:
        prompt: The input prompt
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0 = deterministic)
        
    Returns:
        Generated text response
    """
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        # Return mock response if no API key
        return generate_mock_response(prompt)
    
    # Gemini API endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
    
    # Prepare request payload
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "candidateCount": 1
        }
    }
    
    try:
        # Make API request
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            candidate = data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                return candidate['content']['parts'][0]['text']
        
        return "Error: No valid response from Gemini API"
        
    except requests.exceptions.RequestException as e:
        print(f"Gemini API request failed: {e}")
        return generate_mock_response(prompt)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return generate_mock_response(prompt)


def generate_mock_response(prompt: str) -> str:
    """Generate mock response when Gemini API is unavailable"""
    
    if "summarize" in prompt.lower() or "clause" in prompt.lower():
        # Mock clause summarization response
        return json.dumps({
            "summary": "Legal clause defining company operational parameters and compliance requirements with regulatory frameworks",
            "purpose_tags": ["compliance", "governance", "operations"]
        })
    
    elif "dpr" in prompt.lower() or "sections" in prompt.lower():
        # Mock DPR generation response
        return json.dumps({
            "sections": [
                {
                    "id": "proposal",
                    "title": "Proposal",
                    "body": "This Detailed Project Report (DPR) presents the establishment and operational framework of the Special Purpose Vehicle (SPV). The proposed entity will operate within the prescribed regulatory guidelines while maintaining compliance with applicable corporate governance standards. (CoI p.1)",
                    "source_refs": ["CoI p.1"]
                },
                {
                    "id": "introduction",
                    "title": "Section 2.1: Introduction", 
                    "body": "The SPV has been incorporated to execute specific business objectives as outlined in its Memorandum of Association. The company structure ensures operational efficiency while maintaining transparency in governance and financial management. (MoA p.2)",
                    "source_refs": ["MoA p.2"]
                },
                {
                    "id": "spv_info",
                    "title": "Section 3: SPV Information",
                    "body": "The Special Purpose Vehicle operates under the regulatory framework established by the Companies Act, 2013. Corporate governance practices are implemented to ensure stakeholder protection and operational transparency. (CoI p.1, MoA p.3)",
                    "source_refs": ["CoI p.1", "MoA p.3"]
                },
                {
                    "id": "management",
                    "title": "Section 7: Management Structure",
                    "body": "The management structure comprises qualified professionals with relevant industry experience. The Board of Directors provides strategic oversight while the executive team manages day-to-day operations. (AoA p.5)",
                    "source_refs": ["AoA p.5"]
                },
                {
                    "id": "conclusion",
                    "title": "Section 21: Conclusion",
                    "body": "The SPV structure provides an optimal framework for achieving the stated business objectives while maintaining regulatory compliance. The governance mechanisms ensure accountability and transparency in all operational aspects. (Overall assessment)",
                    "source_refs": ["Overall assessment"]
                }
            ]
        })
    
    else:
        return "Mock response: Gemini API not available. Please set GEMINI_API_KEY environment variable."


def summarize_clause(raw_clause: str) -> dict:
    """
    Convenience function to summarize a legal clause
    
    Args:
        raw_clause: Raw text of the legal clause
        
    Returns:
        Dictionary with summary and purpose tags
    """
    prompt = clause_summarizer_prompt.format(raw_clause=raw_clause)
    response = generate_text(prompt, max_tokens=256, temperature=0.1)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "summary": "Unable to summarize clause",
            "purpose_tags": ["unknown"]
        }


def generate_dpr_sections(spv_info: dict) -> dict:
    """
    Convenience function to generate DPR sections
    
    Args:
        spv_info: Dictionary containing SPV information
        
    Returns:
        Dictionary with generated sections
    """
    prompt = dpr_synthesis_prompt.format(**spv_info)
    response = generate_text(prompt, max_tokens=1024, temperature=0.0)
    
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "sections": [{
                "id": "error",
                "title": "Generation Error",
                "body": "Unable to generate DPR sections",
                "source_refs": []
            }]
        }


# Test function
if __name__ == "__main__":
    # Test clause summarization
    test_clause = """
    The Company shall carry on the business of trading, manufacturing, 
    importing, exporting, buying, selling, dealing in all types of 
    chemicals, pharmaceuticals, and related products.
    """
    
    print("Testing clause summarization:")
    result = summarize_clause(test_clause)
    print(json.dumps(result, indent=2))
    
    print("\nTesting DPR generation:")
    test_spv = {
        "spv_name": "ACME Trading Private Limited",
        "registration_number": "U51909DL2023PTC123456",
        "company_type": "Private Limited",
        "main_objectives": "Trading in chemicals and pharmaceuticals"
    }
    
    result = generate_dpr_sections(test_spv)
    print(json.dumps(result, indent=2))