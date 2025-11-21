"""
Ticket Management Tools for SupportPilot

This module provides tools for managing IT support tickets through a SQLite database.
It implements CRUD operations for ticket lifecycle management:
- Create: Generate new tickets for unresolved issues
- Read: Query ticket status and history
- Update: Modify ticket status (Open → In Progress → Closed)

Tickets are automatically associated with the authenticated user from the session,
ensuring proper access control and audit trails.

Database Schema:
    tickets table:
    - id: Primary key (auto-increment)
    - user_id: Owner of the ticket (TEXT)
    - issue_summary: Brief problem description (TEXT)
    - priority: Low/Normal/High (TEXT)
    - status: Open/In Progress/Closed (TEXT)
    - created_at: Timestamp (DATETIME)

Tools:
    - create_ticket: Creates a new support ticket
    - get_ticket_status: Retrieves user's tickets
    - update_ticket_status: Changes ticket status

Author: SupportPilot Team
"""

import sqlite3
import os
from typing import Optional

# Import ADK's ToolContext to access session state
from google.adk.tools.tool_context import ToolContext

# Define absolute path to database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tickets.db')


def get_db_connection() -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite tickets database.
    
    Returns:
        sqlite3.Connection: Active database connection with Row factory enabled
                           for dictionary-like row access.
    
    Example:
        >>> conn = get_db_connection()
        >>> cursor = conn.cursor()
        >>> cursor.execute("SELECT * FROM tickets")
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def create_ticket(
    issue_summary: str,
    tool_context: ToolContext
) -> str:
    """
    Creates a new support ticket in the database.
    
    The user_id is automatically detected from the session state, ensuring
    tickets are properly attributed to the authenticated user. Manual user_id
    override is available for administrative scenarios.
    
    Args:
        issue_summary (str): A brief description of the technical issue
                            (e.g., "Laptop won't connect to WiFi").
        tool_context (ToolContext): Session context (automatically injected by ADK).
    
    Returns:
        str: Success message with the new Ticket ID, or error message.
        
        Success format: "Ticket created successfully. Ticket ID: {id}"
        Error format: "Error: Could not identify the user." or database errors.
    
    Session State:
        Reads 'user:user_id' from session state for automatic user detection.
    
    Example:
        Agent call:
        >>> create_ticket("Printer is offline", tool_context)
        "Ticket created successfully. Ticket ID: 42"
    
    Security:
        - User identity comes from authenticated session, not user input
        - Prevents users from creating tickets on behalf of others
    """
    # 1. Resolve user_id from session state
    real_user_id = (
        tool_context.state.get("user:user_id") or 
        tool_context.state.get("user_id")
    )
    
    if not real_user_id:
        return "Error: Could not identify the user."
    
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
        
        return f"Ticket created successfully. Ticket ID: {ticket_id}"
    
    except sqlite3.IntegrityError as e:
        return f"Error: Database integrity violation: {str(e)}"
    except Exception as e:
        return f"Error creating ticket: {str(e)}"


def get_ticket_status(
    tool_context: ToolContext
) -> str:
    """
    Retrieves all tickets for a specific user.
    
    The user_id is automatically detected from the session state, ensuring
    users can only view their own tickets (privacy protection).
    
    Args:
        tool_context (ToolContext): Session context (automatically injected by ADK).
    
    Returns:
        str: A formatted report of the user's tickets, or error message.
        
        Success format:
        "Found {count} ticket(s) for user {user_id}:
        - Ticket #{id}: {status} (Issue: {summary})"
        
        No tickets format:
        "No tickets found for user: {user_id}"
    
    Example:
        >>> get_ticket_status(tool_context)
        Found 2 ticket(s) for user alice_123:
        - Ticket #1: Open (Issue: Printer offline)
        - Ticket #5: Closed (Issue: Password reset)
    
    Security:
        - Users can only view their own tickets
        - Admin override available through explicit user_id parameter
    """
    # 1. Resolve user_id from session state
    real_user_id = (
        tool_context.state.get("user:user_id") or 
        tool_context.state.get("user_id")
    )
    
    if not real_user_id:
        return "Error: Could not identify the user."
    
    # 2. Query database for user's tickets
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, issue_summary, status, created_at
            FROM tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (real_user_id,)
        )
        
        tickets = cursor.fetchall()
        conn.close()
        
        # 3. Format response
        if not tickets:
            return f"No tickets found for user: {real_user_id}"
        
        report = [f"Found {len(tickets)} ticket(s) for user {real_user_id}:"]
        
        for ticket in tickets:
            line = (
                f"- Ticket #{ticket['id']}: {ticket['status']} "
                f"(Issue: {ticket['issue_summary']})"
            )
            report.append(line)
        
        return "\n".join(report)
    
    except Exception as e:
        return f"Error retrieving tickets: {str(e)}"


def update_ticket_status(ticket_id: str, new_status: str) -> str:
    """
    Updates the status of an existing ticket.
    
    This tool is typically used by technicians (Level 2 support) to update
    ticket progress. It validates the new status against allowed values and
    ensures the ticket exists before updating.
    
    Args:
        ticket_id (str): The ID of the ticket to update (e.g., "5", "42").
        new_status (str): The new status. Must be one of:
                         'Open', 'In Progress', 'Closed'.
                         Case-insensitive matching is applied.
    
    Returns:
        str: Confirmation message or error message.
        
        Success format: "Success: Ticket #{id} status updated to '{status}'."
        Error format: "Error: Invalid status..." or "Error: Ticket ID not found."
    
    Validation:
        - Status must be one of the three allowed values
        - Ticket ID must exist in the database
        - Case-insensitive status matching for user-friendly input
    
    Example:
        >>> update_ticket_status("5", "closed")
        "Success: Ticket #5 status updated to 'Closed'."
        
        >>> update_ticket_status("999", "Open")
        "Error: Ticket ID 999 not found."
        
        >>> update_ticket_status("5", "InvalidStatus")
        "Error: Invalid status 'InvalidStatus'. Allowed statuses are: Open, In Progress, Closed."
    
    Workflow:
        Open → In Progress → Closed
    """
    # 1. Validate status (case-insensitive matching)
    valid_states = ['Open', 'In Progress', 'Closed']
    
    # Find the correctly capitalized version of the input status
    matched_status = next(
        (s for s in valid_states if s.lower() == new_status.lower()),
        None
    )
    
    if not matched_status:
        return (
            f"Error: Invalid status '{new_status}'. "
            f"Allowed statuses are: {', '.join(valid_states)}."
        )
    
    # 2. Update the ticket in the database
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if ticket exists
        cursor.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,))
        if not cursor.fetchone():
            conn.close()
            return f"Error: Ticket ID {ticket_id} not found."
        
        # Perform update
        cursor.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (matched_status, ticket_id)
        )
        
        conn.commit()
        conn.close()
        
        return f"Success: Ticket #{ticket_id} status updated to '{matched_status}'."
    
    except Exception as e:
        return f"Error updating ticket: {str(e)}"