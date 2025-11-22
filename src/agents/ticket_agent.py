"""
Ticket Agent for SupportPilot

This module defines the Ticket Agent, a specialized agent responsible for
managing IT support tickets throughout their lifecycle.

The Ticket Agent has 4 simple, unambiguous tools that return structured dictionaries:
1. create_ticket: Create new tickets
2. get_ticket_by_id: Get details of ONE specific ticket
3. list_all_tickets: List tickets (auto-filtered by role)
4. update_ticket_status: Update ticket status (service_desk_agent only)

The tools handle all RBAC logic internally and return structured dictionaries,
making it easy for the LlmAgent to process and respond appropriately.

Architecture:
    This agent is invoked by the Orchestrator when users need to:
    - Create a support ticket
    - View a specific ticket by ID
    - List their tickets (or all tickets for service_desk_agent)
    - Update ticket status (service_desk_agent only)

Author: SupportPilot Team
"""

from google.adk.agents.llm_agent import LlmAgent
from src.tools.ticket_tools import (
    create_ticket, 
    get_ticket_by_id,
    list_all_tickets,
    update_ticket_status
)


# Agent instruction (system prompt) - SIMPLIFIED with dictionary support
INSTRUCTION = """
You are 'TicketBot', the Support Ticket Specialist.

YOUR 4 TOOLS (each returns a dictionary with "status" field):

1. **create_ticket(issue_summary)** - Create a new ticket
   Returns: {"status": "success", "ticket_id": 42, "message": "..."}

2. **get_ticket_by_id(ticket_id)** - Get ONE specific ticket
   Returns: {"status": "success", "ticket": {...}, "message": "..."}

3. **list_all_tickets()** - List tickets (auto-filtered by user's role)
   Returns: {"status": "success", "count": 5, "tickets": [...], "message": "..."}

4. **update_ticket_status(ticket_id, new_status)** - Update status
   Returns: {"status": "success", "message": "..."} or {"status": "error", "error_message": "..."}

TOOL SELECTION (Simple - 1:1 mapping):

User mentions a SPECIFIC TICKET NUMBER?
├─ Examples: "ticket 5", "status of ticket 42", "show me ticket 10"
└─ USE: get_ticket_by_id(ticket_id)

User wants to LIST or SEE MULTIPLE tickets?
├─ Examples: "my tickets", "show tickets", "all tickets", "list tickets"
└─ USE: list_all_tickets()

User wants to CREATE a ticket?
├─ Examples: "create ticket for X", "my printer is broken", "need help with Y"
└─ USE: create_ticket(issue_summary)

User wants to UPDATE/CHANGE ticket status?
├─ Examples: "close ticket 5", "mark ticket 3 as in progress", "set ticket 10 to open"
└─ USE: update_ticket_status(ticket_id, new_status)

HANDLING TOOL RESPONSES:

1. Check the "status" field:
   - If "success": Present the information from "message" or data fields clearly
   - If "error": Relay the "error_message" to the user politely

2. Always provide clear, helpful responses:
   - After create: Confirm ticket ID
   - After get_by_id: Present ticket details clearly
   - After list: Present the list in a readable format
   - After update: Confirm the status change
   - On error: Explain what went wrong

3. Be concise but complete:
   - Users want quick, actionable information
   - Don't add unnecessary commentary

EXAMPLES:

User: "Create a ticket for my mouse not working"
YOU: [Call create_ticket("mouse not working")]
Tool returns: {"status": "success", "ticket_id": 42, "message": "Ticket created successfully. Ticket ID: 42"}
YOU: "I've created Ticket #42 for your mouse issue. Our technicians will review it shortly."

User: "What is the status of ticket 5?"
YOU: [Call get_ticket_by_id("5")]
Tool returns: {"status": "success", "ticket": {"id": 5, "status": "Open", ...}, "message": "Ticket #5 (User: alice): Open\n..."}
YOU: "Ticket #5 is currently Open. Issue: Printer offline. Priority: Normal. Created: 2025-01-15."

User: "Show my tickets"
YOU: [Call list_all_tickets()]
Tool returns: {"status": "success", "count": 3, "message": "Found 3 ticket(s):..."}
YOU: "You have 3 tickets:\n- Ticket #1: Open (Printer offline)\n- Ticket #5: Closed (Password reset)\n- Ticket #8: In Progress (VPN issue)"

User: "Close ticket 10"
YOU: [Call update_ticket_status("10", "Closed")]
Tool returns: {"status": "success", "message": "Success: Ticket #10 status updated to 'Closed'."}
YOU: "Ticket #10 has been closed successfully."

User (end_user): "Close ticket 5"
YOU: [Call update_ticket_status("5", "Closed")]
Tool returns: {"status": "error", "error_message": "You do not have permission..."}
YOU: "I'm sorry, but only service desk agents can update ticket status. Your ticket is being handled by our support team."

CRITICAL: Tools handle all permission logic. Just call the right tool and present the result clearly!
"""


def get_ticket_agent() -> LlmAgent:
    """
    Factory function that creates and returns the Ticket Agent instance.
    
    The Ticket Agent is configured with:
    - Model: gemini-2.5-flash-lite (efficient for straightforward CRUD operations)
    - Tools (4 total - all return structured dictionaries):
        * create_ticket: Create new tickets
        * get_ticket_by_id: Query specific ticket by ID (RBAC enforced internally)
        * list_all_tickets: List tickets (auto-filtered by role internally)
        * update_ticket_status: Modify ticket status (RBAC enforced internally)
    - Instruction: Clear tool selection guide with dictionary handling
    
    Returns:
        LlmAgent: Configured Ticket Agent ready to manage support tickets.
    
    Usage:
        This agent is typically invoked by the Orchestrator:
        >>> ticket_bot = get_ticket_agent()
        >>> # Orchestrator routes ticket-related requests to ticket_bot
    
    Design Philosophy:
        - Simplicity: 4 tools with clear, distinct purposes
        - RBAC is invisible: Tools handle all permission logic internally
        - 1:1 mapping: Each user intent maps to exactly ONE tool
        - Structured data: All tools return dictionaries for reliable parsing
        - Enhanced observability: All tools log their calls and returns
    
    Changes from previous version:
        - Changed from Agent to LlmAgent (follows ADK best practices)
        - Tools now return dictionaries instead of strings
        - Simplified instruction - trusts LlmAgent to process dicts correctly
        - Removed "pass-through" mode (no longer needed with proper dict returns)
    """
    return LlmAgent(
        model='gemini-2.5-flash-lite',
        name='ticket_agent',
        description=(
            "Manages support tickets with 4 tools that return structured dictionaries: "
            "create, get by ID, list all (role-filtered), and update status."
        ),
        instruction=INSTRUCTION,
        tools=[
            create_ticket,
            get_ticket_by_id,
            list_all_tickets,
            update_ticket_status
        ]
    )