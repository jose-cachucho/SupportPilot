"""
Custom tools for agent interactions.

All tools use FunctionTool wrappers for ADK integration.
Tools are called autonomously by LLM agents via Runner.

Available tools:
- search_knowledge_base: Search IT support KB (used by KnowledgeAgent)
- create_support_ticket: Create L2 escalation ticket (used by CreationAgent)
- get_ticket_status: Retrieve user's tickets (used by QueryAgent)

Tool functions can also be called directly for testing.
"""

from src.tools.support_tools import (
    # Raw functions (for direct testing)
    search_knowledge_base,
    create_support_ticket,
    get_ticket_status,
    # FunctionTool wrappers (for ADK agents)
    kb_search_tool,
    ticket_creation_tool,
    ticket_query_tool,
    # Collections
    SUPPORT_TOOLS,
    TOOL_FUNCTIONS,
    execute_tool
)

__all__ = [
    # Functions
    "search_knowledge_base",
    "create_support_ticket",
    "get_ticket_status",
    # FunctionTool wrappers
    "kb_search_tool",
    "ticket_creation_tool",
    "ticket_query_tool",
    # Collections
    "SUPPORT_TOOLS",
    "TOOL_FUNCTIONS",
    "execute_tool"
]