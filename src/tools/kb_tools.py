"""
Knowledge Base Tools for SupportPilot

This module provides tools for searching and retrieving solutions from
the IT support knowledge base. It implements keyword-based search to
match user queries with documented solutions.

The knowledge base is stored as a JSON file containing:
- Issue categories (Hardware, Software, Network, etc.)
- Search keywords for efficient matching
- Step-by-step troubleshooting solutions

Tools:
    - search_knowledge_base: Searches for solutions based on user query

Author: SupportPilot Team
"""

import json
import os
from typing import List, Dict, Any

# Define absolute paths to ensure stability regardless of execution context
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KB_PATH = os.path.join(BASE_DIR, 'data', 'knowledge_base.json')


def load_kb() -> List[Dict[str, Any]]:
    """
    Loads the knowledge base data from the JSON file.
    
    Returns:
        List[Dict[str, Any]]: A list of knowledge base entries, where each
                              entry is a dictionary containing:
                              - id: Unique identifier
                              - category: Issue category
                              - issue: Problem description
                              - keywords: List of search terms
                              - solution: Step-by-step resolution steps
                              
                              Returns an empty list if the file is not found.
    
    Example:
        >>> kb = load_kb()
        >>> print(kb[0]['issue'])
        'Printer not responding or printing'
    """
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Warning: Knowledge base not found at {KB_PATH}")
        return []
    except json.JSONDecodeError as e:
        print(f"⚠️  Warning: Invalid JSON in knowledge base: {e}")
        return []


def search_knowledge_base(query: str) -> str:
    """
    Searches the knowledge base for solutions based on a user query.
    
    This function performs a keyword-based search against the knowledge base,
    matching the user's query against:
    1. Keywords field (exact keyword matches)
    2. Issue description (substring matches)
    
    Search Algorithm:
    - Case-insensitive matching
    - Returns top 2 results to avoid context window overflow
    - Prioritizes keyword matches over issue description matches
    
    Args:
        query (str): The user's problem description or keywords
                     (e.g., "printer offline", "vpn connection failed").
    
    Returns:
        str: A formatted string containing matching issue(s) and solution(s).
             Returns "KB_NOT_FOUND" if no matches are found.
             
             Format:
             ISSUE: <problem description>
             SOLUTION: <step-by-step instructions>
    
    Example:
        >>> result = search_knowledge_base("my printer is not working")
        >>> print(result)
        ISSUE: Printer not responding or printing
        SOLUTION: 1. Check if the printer is turned on...
    """
    # Load the knowledge base
    kb_data = load_kb()
    
    # Normalize query to lowercase for case-insensitive matching
    query_lower = query.lower()
    results = []
    
    # Search through each knowledge base entry
    for entry in kb_data:
        # Strategy 1: Check if any keyword exists in the query
        keywords_match = any(
            k.lower() in query_lower 
            for k in entry.get('keywords', [])
        )
        
        # Strategy 2: Check if the query text appears in the issue description
        issue_match = query_lower in entry.get('issue', '').lower()
        
        # If either match succeeds, add to results
        if keywords_match or issue_match:
            formatted_result = (
                f"ISSUE: {entry['issue']}\n"
                f"SOLUTION: {entry['solution']}"
            )
            results.append(formatted_result)
    
    # Return appropriate response
    if not results:
        return "KB_NOT_FOUND"
    
    # Return the top 2 results to avoid overwhelming the agent's context window
    return "\n\n".join(results[:2])