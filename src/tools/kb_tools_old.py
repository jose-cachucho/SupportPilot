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
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                              a knowledge base entry (id, issue, solution, keywords).
                              Returns an empty list if the file is not found.
    """
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Knowledge base not found at {KB_PATH}")
        return []

def search_knowledge_base(query: str) -> str:
    """
    Searches the knowledge base for solutions based on a user query.
    
    It performs a keyword match against the 'keywords' and 'issue' fields
    in the knowledge base.

    Args:
        query (str): The user's problem description or keywords (e.g., "printer offline").

    Returns:
        str: A formatted string containing the matching issue(s) and solution(s).
             Returns "KB_NOT_FOUND" if no matches are found.
    """
    kb_data = load_kb()
    query_lower = query.lower()
    
    results = []
        
    for entry in kb_data:
        # Simple search strategy: Check if any keyword exists in the query
        # or if the query text appears in the issue description.
        keywords_match = any(k.lower() in query_lower for k in entry.get('keywords', []))
        issue_match = query_lower in entry.get('issue', '').lower()
        
        if keywords_match or issue_match:
            formatted_result = (
                f"ISSUE: {entry['issue']}\n"
                f"SOLUTION: {entry['solution']}"
            )
            results.append(formatted_result)   
    
    if not results:
        return "KB_NOT_FOUND"
    
    # Return the top 2 results to avoid overwhelming the context window
    return "\n\n".join(results[:2])