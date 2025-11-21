"""
Session Management Tools for SupportPilot

This module provides tools for managing user session state and identity.
It allows agents to query the current authenticated user's information
from the session context.

In an enterprise environment, user identity is typically provided by:
- Operating system authentication
- SSO (Single Sign-On) tokens
- Active Directory integration

This approach ensures secure identity management without allowing
users to arbitrarily change their identity through conversation.

Tools:
    - get_my_info: Retrieves current user's ID and name from session state

Author: SupportPilot Team
"""

from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext


def get_my_info(tool_context: ToolContext) -> Dict[str, str]:
    """
    Retrieves the current authenticated user's ID and Name from the session state.
    
    This tool reads user identity information that was established at the
    start of the session (typically during login/authentication). The data
    is stored in the session state with the 'user:' prefix for persistence.
    
    Args:
        tool_context (ToolContext): The ADK tool context containing session state.
                                    This parameter is automatically injected by
                                    the ADK framework and should not be provided
                                    manually by the agent.
    
    Returns:
        Dict[str, str]: A structured dictionary containing:
            - status (str): Operation status ("success")
            - user_id (str): The unique user identifier
            - user_name (str): The user's display name
            - message (str): Human-readable confirmation message
    
    Session State Keys:
        - user:user_id: Unique identifier (e.g., "alice_123")
        - user:name: Display name (e.g., "Alice Johnson")
    
    Example:
        When the agent calls this tool, it receives:
        {
            "status": "success",
            "user_id": "alice_123",
            "user_name": "Alice Johnson",
            "message": "The current active user is alice_123."
        }
    
    Security Note:
        User identity cannot be changed during a session. This prevents
        privilege escalation attacks where a user might try to impersonate
        another user by saying "I am Administrator" in conversation.
    """
    # Safely read user identity from session state
    # Defaults to "Unknown"/"Guest" if keys are missing (should not happen in normal flow)
    user_id = tool_context.state.get("user:user_id", "Unknown")
    name = tool_context.state.get("user:name", "Guest")
    
    # Return structured data (easier for LLM to process than plain text)
    return {
        "status": "success",
        "user_id": user_id,
        "user_name": name,
        "message": f"The current active user is {user_id}."
    }