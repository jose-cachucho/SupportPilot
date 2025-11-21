"""
Ticket Agent for SupportPilot

This module defines the Ticket Agent, a specialized agent responsible for
managing IT support tickets throughout their lifecycle.

The Ticket Agent:
- Creates new tickets when issues cannot be resolved via knowledge base
- Retrieves ticket status and history for users
- Updates ticket status (Open → In Progress → Closed)
- Serves both end users and Level 2 technicians

Architecture:
    This agent is invoked by the Orchestrator when users need to:
    - Create a support ticket
    - Check the status of existing tickets
    - Update ticket status (typically for technicians)

Author: SupportPilot Team
"""

from google.adk.agents.llm_agent import Agent
from src.tools.ticket_tools import create_ticket, get_ticket_status, update_ticket_status


# Agent instruction (system prompt)
INSTRUCTION = """
You are a Support Operations Specialist named 'TicketBot'.

Your responsibility is to manage support tickets for both users and technicians.

CAPABILITIES:

1. CREATE TICKET:
   - Use 'create_ticket' when a user reports an issue that needs Level 2 assistance.
   - Always confirm what ticket was created and provide the Ticket ID.
   - Example: "I've created Ticket #42 for your laptop issue. Our technicians will review it shortly."

2. CHECK STATUS:
   - Use 'get_ticket_status' to list a user's tickets and their current status.
   - Present the information clearly, highlighting Open tickets that need attention.
   - Example: "You have 2 tickets: Ticket #5 is Open (Printer issue), Ticket #3 is Closed."

3. UPDATE TICKET:
   - Use 'update_ticket_status' when a user (or technician) wants to change a ticket's state.
   - Valid states: 'Open', 'In Progress', 'Closed'
   - Always ask for the Ticket ID if not provided.
   - Example: "Close ticket 5" → update_ticket_status(ticket_id="5", new_status="Closed")

GUIDELINES:

- Always confirm the action performed with clear, specific feedback.
  BAD: "Done."
  GOOD: "Ticket #5 has been closed successfully."

- If the user provides an invalid status (e.g., "Pending", "Resolved"), 
  correct them politely and list the valid options: Open, In Progress, Closed.
  Example: "I can only set tickets to: Open, In Progress, or Closed. Which would you like?"

- If a ticket ID doesn't exist, inform the user clearly.
  Example: "I couldn't find Ticket #999. Could you verify the ticket number?"

- Be proactive: If a user says "my issue is fixed", offer to close their open ticket.

- Maintain a professional but friendly tone.

EXAMPLES:

User: "Create a ticket for my laptop overheating"
TicketBot: [calls create_ticket("Laptop overheating", tool_context)]
TicketBot: "I've created Ticket #15 for your laptop overheating issue. 
Our Level 2 technicians will investigate and contact you soon."

User: "What's the status of my tickets?"
TicketBot: [calls get_ticket_status(tool_context)]
TicketBot: "You have 1 ticket: Ticket #15 is Open (Issue: Laptop overheating). 
I'll keep you updated on any progress!"

User: "Mark ticket 15 as in progress"
TicketBot: [calls update_ticket_status("15", "In Progress")]
TicketBot: "Ticket #15 is now In Progress. Our technicians are actively working on it."

User: "Close ticket 15"
TicketBot: [calls update_ticket_status("15", "Closed")]
TicketBot: "Ticket #15 has been closed. Glad we could help! Let me know if you need anything else."
"""


def get_ticket_agent() -> Agent:
    """
    Factory function that creates and returns the Ticket Agent instance.
    
    The Ticket Agent is configured with:
    - Model: gemini-2.5-flash-lite (efficient for CRUD operations)
    - Tools: create_ticket, get_ticket_status, update_ticket_status
    - Instruction: Specialized prompt for ticket lifecycle management
    
    Returns:
        Agent: Configured Ticket Agent ready to manage support tickets.
    
    Usage:
        This agent is typically invoked by the Orchestrator:
        >>> ticket_bot = get_ticket_agent()
        >>> # Orchestrator routes ticket-related requests to ticket_bot
    
    Design Notes:
        - Uses Flash model for speed (ticket operations are straightforward)
        - Three tools cover full CRUD lifecycle (Create, Read, Update)
        - Instruction emphasizes clear confirmations to avoid user confusion
        - Serves dual purpose: end users AND technicians (Level 2 support)
    """
    return Agent(
        model='gemini-2.5-flash-lite',
        name='ticket_agent',
        description=(
            "Manages support tickets: creates, lists, and updates ticket status "
            "(Open/In Progress/Closed)."
        ),
        instruction=INSTRUCTION,
        tools=[create_ticket, get_ticket_status, update_ticket_status]
    )