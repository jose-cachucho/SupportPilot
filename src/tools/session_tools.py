"""
Session Management Tools for SupportPilot

This module provides tools for managing user session state and identity.
It allows agents to query the current authenticated user's information
including their ID, name, and role from the session context.

In an enterprise environment, user identity and role are typically provided by:
- Operating system authentication
- SSO (Single Sign-On) tokens
- Active Directory integration
- RBAC (Role-Based Access Control) systems

This approach ensures secure identity management without allowing
users to arbitrarily change their identity or role through conversation.

Tools:
    - get_my_info: Retrieves current user's ID, name, and role from session state

Author: SupportPilot Team
"""

from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext

# Import logger for enhanced observability
from src.utils.logger import setup_logger

# Initialize logger for this module
logger = setup_logger("SessionTools")


def get_my_info(tool_context: ToolContext) -> Dict[str, str]:
    """
    Retrieves the current authenticated user's ID, Name, and Role from the session state.
    
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
            - user_role (str): The user's role ("end_user" or "service_desk_agent")
            - message (str): Human-readable confirmation message with role
    
    Session State Keys:
        - user:user_id: Unique identifier (e.g., "alice_123")
        - user:name: Display name (e.g., "Alice Johnson")
        - user:role: User role (e.g., "end_user", "service_desk_agent")
    
    Roles:
        - end_user: Regular users who can create tickets and view their own tickets
        - service_desk_agent: Support staff who can view all tickets and update status
    
    Example:
        When the agent calls this tool for a service desk agent, it receives:
        {
            "status": "success",
            "user_id": "john_support",
            "user_name": "John Support",
            "user_role": "service_desk_agent",
            "message": "The current active user is john_support (Service Desk Agent)."
        }
    
    Security Note:
        User identity and role cannot be changed during a session. This prevents
        privilege escalation attacks where a user might try to impersonate
        another user or elevate their permissions by conversation.
    """
    # Safely read user identity from session state
    # Defaults to "Unknown"/"Guest"/"end_user" if keys are missing
    user_id = tool_context.state.get("user:user_id", "Unknown")
    name = tool_context.state.get("user:name", "Guest")
    role = tool_context.state.get("user:role", "end_user")  # Default to end_user
    
    # Enhanced logging: Log function entry
    logger.info(
        f"[TOOL_CALL] get_my_info | "
        f"User: {user_id} | Role: {role}"
    )
    
    # Format role for display (convert snake_case to Title Case)
    role_display = role.replace('_', ' ').title()
    
    # Return structured data (easier for LLM to process than plain text)
    result = {
        "status": "success",
        "user_id": user_id,
        "user_name": name,
        "user_role": role,
        "message": f"The current active user is {user_id} ({role_display})."
    }
    
    # Enhanced logging: Log function exit
    logger.info(
        f"[TOOL_RETURN] get_my_info | "
        f"Success: Returned info for {user_id} ({role})"
    )
    
    return result