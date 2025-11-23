"""
SupportPilot Tools Package

Contains custom tools that return structured dictionaries following ADK best practices:
- Ticket Tools: CRUD operations for support tickets
- KB Tools: Knowledge base search
- Session Tools: User identity and role management

Author: SupportPilot Team
"""

from src.tools.ticket_tools import (
    create_ticket,
    get_ticket_by_id,
    list_all_tickets,
    update_ticket_status
)
from src.tools.kb_tools import search_knowledge_base
from src.tools.session_tools import get_my_info

__all__ = [
    'create_ticket',
    'get_ticket_by_id',
    'list_all_tickets',
    'update_ticket_status',
    'search_knowledge_base',
    'get_my_info',
]