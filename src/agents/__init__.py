"""
SupportPilot Agents Package

Contains specialized LLM agents for the multi-agent architecture:
- Orchestrator: Main coordinator agent
- Knowledge Agent: Technical troubleshooting via KB search
- Ticket Agent: Ticket lifecycle management

Author: SupportPilot Team
"""

from src.agents.orchestrator import get_orchestrator_agent
from src.agents.knowledge_agent import get_knowledge_agent
from src.agents.ticket_agent import get_ticket_agent

__all__ = [
    'get_orchestrator_agent',
    'get_knowledge_agent',
    'get_ticket_agent',
]