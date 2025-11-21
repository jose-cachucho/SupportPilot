from google.adk.agents.llm_agent import Agent
from src.tools.ticket_tools import create_ticket, get_ticket_status, update_ticket_status

INSTRUCTION = """
You are a Support Operations Specialist named 'TicketBot'.
Your responsibility is to manage support tickets for both users and technicians.

CAPABILITIES:
1. CREATE TICKET: Use 'create_ticket' when a user reports an issue.
2. CHECK STATUS: Use 'get_ticket_status' to list tickets.
3. UPDATE TICKET: Use 'update_ticket_status' when a user (or technician) wants to change a ticket's state.
   - Valid states: 'Open', 'In Progress', 'Closed'.
   - Example: "Close ticket 5" -> update_ticket_status(ticket_id="5", new_status="Closed").

GUIDELINES:
- Always confirm the action performed.
- If the user provides an invalid status, correct them politely listing the valid options.
"""

def get_ticket_agent():
    return Agent(
        model='gemini-2.5-flash-lite',
        name='ticket_agent',
        description="Manages support tickets: creates, lists, and updates ticket status (Open/In Progress/Closed).",
        instruction=INSTRUCTION,
        # ADICIONAR AQUI A NOVA TOOL À LISTA
        tools=[create_ticket, get_ticket_status, update_ticket_status]
    )