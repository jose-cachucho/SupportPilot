"""
Custom Tools for SupportPilot ADK Agents (ADK-Native)

These tools use the ADK FunctionTool wrapper for seamless integration
with the Agent class. The ADK automatically extracts descriptions from
docstrings and handles parameter validation.
"""

from typing import Dict, Any, List
from google.adk.tools import FunctionTool
from src.core.database import get_database, get_knowledge_base


# ============================================================================
# TOOL 1: Search Knowledge Base
# ============================================================================

def search_knowledge_base(query: str) -> Dict[str, Any]:
    """
    Search the IT support knowledge base for solutions to common problems.
    
    This tool should be used when a user reports a technical issue that might
    have a known solution (e.g., VPN problems, password resets, software issues).
    
    The knowledge base contains step-by-step solutions for frequently asked
    questions and common IT problems. It uses keyword matching to find relevant
    articles.
    
    Args:
        query: The user's problem description. Should be a clear statement
               of the technical issue (e.g., "VPN won't connect" or 
               "forgot my password").
    
    Returns:
        A dictionary containing:
            - found (bool): Whether a matching solution was found
            - solution (str|None): Step-by-step solution if found
            - article_id (str|None): KB article identifier (e.g., "kb-001")
            - title (str|None): Article title
            - category (str|None): Problem category (e.g., "network", "authentication")
    
    Examples:
        >>> search_knowledge_base("my vpn is not working")
        {
            "found": True,
            "solution": "1. Check your internet...",
            "article_id": "kb-001",
            "title": "VPN Connection Troubleshooting",
            "category": "network"
        }
        
        >>> search_knowledge_base("quantum computing")
        {
            "found": False,
            "solution": None,
            "article_id": None,
            "title": None,
            "category": None
        }
    
    When to use:
        - User describes a technical problem
        - Before escalating to ticket creation
        - When user asks "how do I..." questions
    
    When NOT to use:
        - User explicitly asks to create a ticket
        - User asks about their existing tickets
        - User expresses dissatisfaction with a previous KB solution
    """
    kb = get_knowledge_base()
    result = kb.search(query)
    
    if result:
        return {
            "found": True,
            "solution": result["solution"],
            "article_id": result["id"],
            "title": result["title"],
            "category": result["category"]
        }
    else:
        return {
            "found": False,
            "solution": None,
            "article_id": None,
            "title": None,
            "category": None
        }


# ============================================================================
# TOOL 2: Create Support Ticket
# ============================================================================

def create_support_ticket(
    user_id: str,
    description: str,
    priority: str = "Normal",
    trace_id: str = None
) -> Dict[str, Any]:
    """
    Create a new support ticket for escalation to L2 (human) support.
    
    This tool should be used when:
    1. The knowledge base doesn't have a solution (search_knowledge_base returned found=False)
    2. The user explicitly requests a ticket
    3. The user is dissatisfied with KB solutions (says "this didn't work", "still broken", etc.)
    4. The problem is complex and requires human intervention
    
    Creating a ticket escalates the issue to Level 2 support staff who will
    follow up with the user directly.
    
    Args:
        user_id: Unique identifier for the user requesting support.
                 Format: alphanumeric string (e.g., "user_123", "john.doe")
        
        description: Clear, detailed description of the problem.
                     Should include:
                     - What the user is trying to do
                     - What went wrong
                     - Any error messages
                     - Steps already attempted (if any)
                     Example: "User cannot connect to VPN. Error: 'Authentication failed'. 
                              Tried restarting router and VPN client as per KB-001."
        
        priority: Ticket priority level. Must be one of:
                  - "Low": Minor issues, no work stoppage
                  - "Normal": Regular issues (default)
                  - "High": Critical issues blocking work
                  Default: "Normal"
        
        trace_id: Internal trace ID for observability (automatically set by orchestrator)
    
    Returns:
        A dictionary containing:
            - success (bool): Whether ticket was created successfully
            - ticket_id (str): Formatted ticket identifier (e.g., "TICKET-1001")
            - message (str): User-friendly confirmation message
            - estimated_response (str): Expected response time
    
    Examples:
        >>> create_support_ticket(
        ...     user_id="alice_123",
        ...     description="Cannot access shared drive. Error 0x80070035",
        ...     priority="High"
        ... )
        {
            "success": True,
            "ticket_id": "TICKET-1005",
            "message": "Support ticket TICKET-1005 has been created...",
            "estimated_response": "4 business hours"
        }
    
    When to use:
        - After search_knowledge_base returns found=False
        - User says "create ticket", "I need help", "escalate this"
        - User says "that didn't work" after trying a KB solution
    
    When NOT to use:
        - As first action (always try KB first unless explicit ticket request)
        - When user is just asking for ticket status
    """
    db = get_database()
    
    # Validate inputs
    if not description or description.strip() == "":
        return {
            "success": False,
            "ticket_id": None,
            "message": "Error: Ticket description cannot be empty",
            "estimated_response": None
        }
    
    # Validate priority
    valid_priorities = ["Low", "Normal", "High"]
    if priority not in valid_priorities:
        priority = "Normal"
    
    # Create ticket
    ticket_id = db.create_ticket(
        user_id=user_id,
        description=description,
        trace_id=trace_id,
        priority=priority
    )
    
    # Determine response time based on priority
    response_times = {
        "Low": "2 business days",
        "Normal": "1 business day",
        "High": "4 business hours"
    }
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": f"Support ticket {ticket_id} has been created successfully. "
                   f"L2 support will contact you within {response_times[priority]}.",
        "estimated_response": response_times[priority]
    }


# ============================================================================
# TOOL 3: Get Ticket Status
# ============================================================================

def get_ticket_status(user_id: str) -> Dict[str, Any]:
    """
    Retrieve all support tickets for a specific user.
    
    This tool provides self-service access to ticket information, allowing
    users to check the status of their support requests without contacting
    human support.
    
    Args:
        user_id: Unique identifier for the user.
                 Must match the user_id used when creating tickets.
                 Format: alphanumeric string (e.g., "user_123")
    
    Returns:
        A dictionary containing:
            - found (bool): Whether any tickets exist for this user
            - count (int): Total number of tickets found
            - tickets (List[Dict]): List of ticket details, each containing:
                - ticket_id (str): Formatted ID (e.g., "TICKET-1001")
                - description (str): Problem description
                - status (str): Current status ("Open", "In Progress", or "Closed")
                - priority (str): "Low", "Normal", or "High"
                - created_at (str): Creation timestamp (ISO format)
                - updated_at (str): Last update timestamp
    
    Examples:
        >>> get_ticket_status(user_id="alice_123")
        {
            "found": True,
            "count": 2,
            "tickets": [
                {
                    "ticket_id": "TICKET-1005",
                    "description": "Cannot access shared drive",
                    "status": "In Progress",
                    "priority": "High",
                    "created_at": "2025-11-15 09:30:00",
                    "updated_at": "2025-11-15 10:15:00"
                },
                ...
            ]
        }
        
        >>> get_ticket_status(user_id="new_user")
        {
            "found": False,
            "count": 0,
            "tickets": []
        }
    
    When to use:
        - User asks "what are my tickets?"
        - User asks "check my ticket status"
        - User asks "do I have any open tickets?"
        - User references a specific ticket ID
    
    When NOT to use:
        - When user is describing a NEW problem (use search_knowledge_base first)
        - When user wants to CREATE a ticket (use create_support_ticket)
    """
    db = get_database()
    tickets = db.get_user_tickets(user_id)
    
    return {
        "found": len(tickets) > 0,
        "count": len(tickets),
        "tickets": tickets
    }


# ============================================================================
# ADK FunctionTool Wrappers
# ============================================================================

# Wrap each function with FunctionTool for ADK Agent integration
kb_search_tool = FunctionTool(func=search_knowledge_base)
ticket_creation_tool = FunctionTool(func=create_support_ticket)
ticket_query_tool = FunctionTool(func=get_ticket_status)


# Export tools list for easy import
SUPPORT_TOOLS = [
    kb_search_tool,
    ticket_creation_tool,
    ticket_query_tool
]


# Tool name mapping for manual execution (if needed)
TOOL_FUNCTIONS = {
    "search_knowledge_base": search_knowledge_base,
    "create_support_ticket": create_support_ticket,
    "get_ticket_status": get_ticket_status
}


def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> Any:
    """
    Execute a tool by name with given parameters.
    
    This is a fallback for direct tool execution outside of the Agent framework.
    Normally, the ADK Agent handles tool execution automatically.
    
    Args:
        tool_name: Name of the tool to execute
        parameters: Dictionary of parameters to pass to the tool
        
    Returns:
        Tool execution result (format depends on the specific tool)
    
    Raises:
        ValueError: If tool_name is not recognized
    """
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_func = TOOL_FUNCTIONS[tool_name]
    return tool_func(**parameters)