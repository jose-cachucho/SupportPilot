"""
Ticket Management Tools for SupportPilot

This module provides tools for managing IT support tickets through a SQLite database.
It implements CRUD operations for ticket lifecycle management with role-based access
control (RBAC) enforced internally within each tool.

The tools are designed to be simple and unambiguous:
1. create_ticket: Create new tickets
2. get_ticket_by_id: Get ONE specific ticket by ID (RBAC enforced)
3. list_all_tickets: List tickets (auto-filtered by role internally)
4. update_ticket_status: Update ticket status (service_desk_agent only)

Database Schema:
    tickets table:
    - id: Primary key (auto-increment)
    - user_id: Owner of the ticket (TEXT)
    - issue_summary: Brief problem description (TEXT)
    - priority: Low/Normal/High (TEXT)
    - status: Open/In Progress/Closed (TEXT)
    - created_at: Timestamp (DATETIME)

Author: SupportPilot Team
"""

import sqlite3
import os
from typing import Optional

# Import ADK's ToolContext to access session state
from google.adk.tools.tool_context import ToolContext

# Import logger for enhanced observability
from src.utils.logger import setup_logger

# Define absolute path to database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tickets.db')

# Initialize logger for this module
logger = setup_logger("TicketTools")


def get_db_connection() -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite tickets database.
    
    Returns:
        sqlite3.Connection: Active database connection with Row factory enabled
                           for dictionary-like row access.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def create_ticket(
    issue_summary: str,
    tool_context: ToolContext
) -> dict:
    """
    Creates a new support ticket in the database.
    
    The user_id is automatically detected from the session state, ensuring
    tickets are properly attributed to the authenticated user.
    
    Args:
        issue_summary (str): A brief description of the technical issue
                            (e.g., "Laptop won't connect to WiFi").
        tool_context (ToolContext): Session context (automatically injected by ADK).
    
    Returns:
        dict: Structured response with status and ticket information.
        
        Success format:
        {
            "status": "success",
            "ticket_id": 42
        }
        
        Error format:
        {
            "status": "error",
            "error_message": "Could not identify the user."
        }
    
    Session State:
        Reads 'user:user_id' and 'user:role' from session state.
    
    Example:
        >>> create_ticket("Printer is offline", tool_context)
        {"status": "success", "ticket_id": 42}
    
    Security:
        - User identity comes from authenticated session, not user input
        - Prevents users from creating tickets on behalf of others
    """
    # 1. Resolve user_id from session state
    real_user_id = (
        tool_context.state.get("user:user_id") or 
        tool_context.state.get("user_id")
    )
    role = tool_context.state.get("user:role", "end_user")
    
    # Enhanced logging: Log function entry
    logger.info(
        f"[TOOL_CALL] create_ticket | "
        f"User: {real_user_id} | Role: {role} | "
        f"Issue: {issue_summary[:50]}..."
    )
    
    if not real_user_id:
        error_result = {
            "status": "error",
            "error_message": "Could not identify the user."
        }
        logger.error(f"[TOOL_RETURN] create_ticket | {error_result}")
        return error_result
    
    # 2. Set default priority (hardcoded since defaults not supported by Google AI)
    priority = "Normal"
    
    # 3. Insert ticket into database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO tickets (user_id, issue_summary, priority, status)
            VALUES (?, ?, ?, ?)
            """,
            (real_user_id, issue_summary, priority, 'Open')
        )
        
        ticket_id = cursor.lastrowid  # Get the newly created ticket's ID
        conn.commit()
        conn.close()
        
        result = {
            "status": "success",
            "ticket_id": ticket_id
        }
        
        # Enhanced logging: Log function exit with result
        logger.info(
            f"[TOOL_RETURN] create_ticket | "
            f"Success: Ticket #{ticket_id} created for {real_user_id}"
        )
        
        return result
    
    except sqlite3.IntegrityError as e:
        error_result = {
            "status": "error",
            "error_message": f"Database integrity violation: {str(e)}"
        }
        logger.error(f"[TOOL_RETURN] create_ticket | {error_result}")
        return error_result
    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": f"Error creating ticket: {str(e)}"
        }
        logger.error(f"[TOOL_RETURN] create_ticket | {error_result}")
        return error_result


def get_ticket_by_id(ticket_id: str, tool_context: ToolContext) -> dict:
    """
    Retrieves detailed information about a specific ticket by its ID (RBAC enforced).
    
    Returns ticket data in a clean structured format for easy agent interpretation.
    
    Access Control:
        - end_user: Can only view tickets they own
        - service_desk_agent: Can view any ticket in the system
    
    Args:
        ticket_id (str): The ticket ID to query (e.g., "5", "42").
        tool_context (ToolContext): Session context (automatically injected by ADK).
    
    Returns:
        dict: Structured response with ticket details or error.
        
        Success format:
        {
            "status": "success",
            "ticket": {
                "id": 5,
                "user_id": "alice_123",
                "status": "Open",
                "issue": "Printer not responding",
                "priority": "Normal",
                "created_at": "2025-01-15 10:30:00"
            }
        }
        
        Error formats:
        {
            "status": "error",
            "error_message": "Ticket ID 5 not found."
        }
        or
        {
            "status": "error",
            "error_message": "You do not have permission to view this ticket."
        }
    
    Security:
        - end_users cannot access tickets belonging to other users
        - service_desk_agents have full visibility for support operations
        - Prevents unauthorized information disclosure
    """
    # 1. Resolve user_id and role from session state
    user_id = tool_context.state.get("user:user_id") or tool_context.state.get("user_id")
    role = tool_context.state.get("user:role", "end_user")
    
    # Enhanced logging: Log function entry
    logger.info(
        f"[TOOL_CALL] get_ticket_by_id | "
        f"Ticket ID: {ticket_id} | User: {user_id} | Role: {role}"
    )
    
    if not user_id:
        error_result = {
            "status": "error",
            "error_message": "Could not identify the user."
        }
        logger.error(f"[TOOL_RETURN] get_ticket_by_id | {error_result}")
        return error_result
    
    # 2. Query database for the specific ticket
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, user_id, issue_summary, priority, status, created_at
            FROM tickets
            WHERE id = ?
            """,
            (ticket_id,)
        )
        
        ticket = cursor.fetchone()
        conn.close()
        
        # 3. Check if ticket exists
        if not ticket:
            error_result = {
                "status": "error",
                "error_message": f"Ticket ID {ticket_id} not found."
            }
            logger.warning(f"[TOOL_RETURN] get_ticket_by_id | {error_result}")
            return error_result
        
        # 4. RBAC: Check if user has permission to view this ticket
        if role == "end_user" and ticket['user_id'] != user_id:
            error_result = {
                "status": "error",
                "error_message": "You do not have permission to view this ticket. You can only view your own tickets."
            }
            logger.warning(
                f"[TOOL_RETURN] get_ticket_by_id | "
                f"Permission denied: {user_id} tried to access ticket #{ticket_id} "
                f"owned by {ticket['user_id']}"
            )
            return error_result
        
        # 5. Return clean structured data (NO message field for success)
        result = {
            "status": "success",
            "ticket": {
                "id": ticket['id'],
                "user_id": ticket['user_id'],
                "status": ticket['status'],
                "issue": ticket['issue_summary'],
                "priority": ticket['priority'],
                "created_at": ticket['created_at']
            }
        }
        
        # Enhanced logging: Log function exit with result summary
        logger.info(
            f"[TOOL_RETURN] get_ticket_by_id | "
            f"Success: Returned ticket #{ticket_id} ({ticket['status']}) "
            f"to {user_id} ({role})"
        )
        
        return result
    
    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": f"Error retrieving ticket: {str(e)}"
        }
        logger.error(f"[TOOL_RETURN] get_ticket_by_id | {error_result}")
        return error_result


def list_all_tickets(tool_context: ToolContext) -> dict:
    """
    Lists tickets with automatic role-based filtering (RBAC internal).
    
    This tool provides a unified interface for listing tickets. The filtering
    is handled INTERNALLY based on the user's role, making it transparent to
    the agent calling this tool.
    
    Access Control (Automatic):
        - end_user: Automatically filtered to show ONLY their tickets
        - service_desk_agent: Automatically shows ALL tickets in the system
    
    Args:
        tool_context (ToolContext): Session context (automatically injected by ADK).
    
    Returns:
        dict: Structured response with list of tickets or error.
        
        Success format:
        {
            "status": "success",
            "count": 15,
            "tickets": [
                {
                    "id": 1,
                    "user_id": "alice_123",
                    "status": "Open",
                    "issue": "Printer offline",
                    "priority": "Normal",
                    "created_at": "2025-01-15 10:30:00"
                },
                ...
            ]
        }
        
        No tickets format:
        {
            "status": "success",
            "count": 0,
            "tickets": []
        }
    
    Security:
        - Automatic data isolation for end_users
        - System-wide visibility for service_desk_agents
        - No explicit permission checking needed (handled by SQL WHERE clause)
    """
    # 1. Resolve user_id and role from session state
    user_id = tool_context.state.get("user:user_id") or tool_context.state.get("user_id")
    role = tool_context.state.get("user:role", "end_user")
    
    # Enhanced logging: Log function entry
    logger.info(
        f"[TOOL_CALL] list_all_tickets | "
        f"User: {user_id} | Role: {role}"
    )
    
    if not user_id:
        error_result = {
            "status": "error",
            "error_message": "Could not identify the user."
        }
        logger.error(f"[TOOL_RETURN] list_all_tickets | {error_result}")
        return error_result
    
    # 2. Query database with AUTOMATIC role-based filtering
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # RBAC: Automatic filtering based on role
        if role == "service_desk_agent":
            # Service desk sees ALL tickets
            cursor.execute(
                """
                SELECT id, user_id, issue_summary, status, priority, created_at
                FROM tickets
                ORDER BY created_at DESC
                """
            )
            logger.debug(f"[SQL] Fetching ALL tickets (service_desk_agent)")
        else:
            # end_user sees ONLY their tickets
            cursor.execute(
                """
                SELECT id, user_id, issue_summary, status, priority, created_at
                FROM tickets
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            logger.debug(f"[SQL] Fetching tickets for user: {user_id} (end_user)")
        
        tickets = cursor.fetchall()
        conn.close()
        
        # 3. Format response - clean structured data only
        ticket_list = []
        
        for ticket in tickets:
            ticket_dict = {
                "id": ticket['id'],
                "user_id": ticket['user_id'],
                "status": ticket['status'],
                "issue": ticket['issue_summary'],
                "priority": ticket['priority'],
                "created_at": ticket['created_at']
            }
            ticket_list.append(ticket_dict)
        
        result = {
            "status": "success",
            "count": len(tickets),
            "tickets": ticket_list
        }
        
        # Enhanced logging: Log function exit with result summary
        logger.info(
            f"[TOOL_RETURN] list_all_tickets | "
            f"Success: Returned {len(tickets)} ticket(s) to {user_id} ({role})"
        )
        
        return result
    
    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": f"Error listing tickets: {str(e)}"
        }
        logger.error(f"[TOOL_RETURN] list_all_tickets | {error_result}")
        return error_result


def update_ticket_status(
    ticket_id: str, 
    new_status: str, 
    tool_context: ToolContext
) -> dict:
    """
    Updates the status of an existing ticket (RESTRICTED to service_desk_agent).
    
    This tool implements Role-Based Access Control (RBAC):
    - Only users with role "service_desk_agent" can update ticket status
    - end_users will receive a permission denied error
    
    This reflects real-world IT operations where only Level 2 support staff
    can modify ticket status after investigating/resolving issues.
    
    Args:
        ticket_id (str): The ID of the ticket to update (e.g., "5", "42").
        new_status (str): The new status. Must be one of:
                         'Open', 'In Progress', 'Closed'.
                         Case-insensitive matching is applied.
        tool_context (ToolContext): Session context (automatically injected by ADK).
    
    Returns:
        dict: Structured response with status update confirmation or error.
        
        Success format: 
        {
            "status": "success",
            "ticket_id": 5,
            "new_status": "Closed"
        }
        
        Permission denied format:
        {
            "status": "error",
            "error_message": "You do not have permission to update ticket status. Only service desk agents can modify tickets."
        }
        
        Error format: 
        {
            "status": "error",
            "error_message": "Invalid status 'Pending'. Allowed statuses are: Open, In Progress, Closed."
        }
    
    Validation:
        - Role must be "service_desk_agent"
        - Status must be one of the three allowed values
        - Ticket ID must exist in the database
        - Case-insensitive status matching for user-friendly input
    
    Workflow:
        Open → In Progress → Closed
    
    Security:
        - RBAC prevents unauthorized ticket modifications
        - Maintains audit trail of who can change ticket states
        - Protects against end_users closing tickets prematurely
    """
    # 1. Resolve user_id and role from session state
    user_id = tool_context.state.get("user:user_id") or tool_context.state.get("user_id")
    role = tool_context.state.get("user:role", "end_user")
    
    # Enhanced logging: Log function entry
    logger.info(
        f"[TOOL_CALL] update_ticket_status | "
        f"Ticket ID: {ticket_id} | New Status: {new_status} | "
        f"User: {user_id} | Role: {role}"
    )
    
    # 2. Check user role (RBAC enforcement)
    if role != "service_desk_agent":
        error_result = {
            "status": "error",
            "error_message": "You do not have permission to update ticket status. Only service desk agents can modify tickets."
        }
        logger.warning(
            f"[TOOL_RETURN] update_ticket_status | "
            f"Permission denied: {user_id} ({role}) tried to update ticket #{ticket_id}"
        )
        return error_result
    
    # 3. Validate status (case-insensitive matching)
    valid_states = ['Open', 'In Progress', 'Closed']
    
    # Find the correctly capitalized version of the input status
    matched_status = next(
        (s for s in valid_states if s.lower() == new_status.lower()),
        None
    )
    
    if not matched_status:
        error_result = {
            "status": "error",
            "error_message": f"Invalid status '{new_status}'. Allowed statuses are: {', '.join(valid_states)}."
        }
        logger.warning(f"[TOOL_RETURN] update_ticket_status | {error_result}")
        return error_result
    
    # 4. Update the ticket in the database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if ticket exists
        cursor.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,))
        if not cursor.fetchone():
            conn.close()
            error_result = {
                "status": "error",
                "error_message": f"Ticket ID {ticket_id} not found."
            }
            logger.warning(f"[TOOL_RETURN] update_ticket_status | {error_result}")
            return error_result
        
        # Perform update
        cursor.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (matched_status, ticket_id)
        )
        
        conn.commit()
        conn.close()
        
        result = {
            "status": "success",
            "ticket_id": int(ticket_id),
            "new_status": matched_status
        }
        
        # Enhanced logging: Log function exit with result
        logger.info(
            f"[TOOL_RETURN] update_ticket_status | "
            f"Success: Ticket #{ticket_id} updated to '{matched_status}' by {user_id}"
        )
        
        return result
    
    except Exception as e:
        error_result = {
            "status": "error",
            "error_message": f"Error updating ticket: {str(e)}"
        }
        logger.error(f"[TOOL_RETURN] update_ticket_status | {error_result}")
        return error_result