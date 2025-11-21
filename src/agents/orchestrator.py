from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool 

from src.agents.knowledge_agent import get_knowledge_agent
from src.agents.ticket_agent import get_ticket_agent
# REMOVIDO: switch_active_user
from src.tools.session_tools import get_my_info

# Instrução Simplificada
ORCHESTRATOR_INSTRUCTION = """
You are 'SupportPilot', the main IT Support Coordinator.
Your job is to triage requests and manage the user session.

AVAILABLE TOOLS:
1. knowledge_agent: For technical questions/troubleshooting.
2. ticket_agent: For creating/updating/checking tickets.
3. get_my_info: Use this if the user asks who they are. IMPORTANT: You MUST explicitly tell the user their ID and Name returned by this tool.

IMPORTANT:
- Always be polite and helpful.
"""

def get_orchestrator_agent():
    knowledge_bot = get_knowledge_agent()
    ticket_bot = get_ticket_agent()

    return Agent(
        model='gemini-2.5-flash-lite',
        name='support_pilot_orchestrator',
        description="Main coordinator. Routes requests and manages user identity.",
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            AgentTool(knowledge_bot), 
            AgentTool(ticket_bot),
            get_my_info
            # REMOVIDO: switch_active_user
        ]
    )