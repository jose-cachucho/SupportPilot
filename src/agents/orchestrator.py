"""
Orchestrator Agent for SupportPilot

This module defines the Orchestrator, the main coordinator agent responsible
for triaging user requests and delegating tasks to specialized sub-agents.

The Orchestrator:
- Serves as the primary user interface (first point of contact)
- Routes technical questions to the Knowledge Agent
- Routes ticket operations to the Ticket Agent
- Manages user session and identity
- Maintains conversational context across interactions

Architecture:
    Multi-Agent System (Sequential):
    
    User → Orchestrator → Knowledge Agent (technical queries)
                      ↘ Ticket Agent (ticket operations)
                      ↘ Session Tools (identity management)

    The Orchestrator uses ADK's AgentTool to invoke sub-agents dynamically
    based on user intent.

Author: SupportPilot Team
"""

from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool

from src.agents.knowledge_agent import get_knowledge_agent
from src.agents.ticket_agent import get_ticket_agent
from src.tools.session_tools import get_my_info


# Orchestrator instruction (system prompt)
ORCHESTRATOR_INSTRUCTION = """
You are 'SupportPilot', the main IT Support Coordinator.

Your job is to triage user requests and route them to the appropriate specialist agent.

AVAILABLE TOOLS:

1. knowledge_agent:
   - Use for technical questions and troubleshooting.
   - Examples: "My printer won't print", "VPN connection failed", "Outlook not syncing"
   - This agent searches the knowledge base for documented solutions.

2. ticket_agent:
   - Use for ticket management operations.
   - Examples: "Create a ticket", "What's my ticket status?", "Close ticket 5"
   - This agent handles the full ticket lifecycle (create, read, update).

3. get_my_info:
   - Use if the user asks who they are or requests their user information.
   - IMPORTANT: You MUST explicitly tell the user their ID and Name returned by this tool.
   - Don't stay silent after calling this tool - communicate the result!
   - Example: "You are logged in as alice_123 (Alice)."

ROUTING LOGIC:

Step 1: Identify Intent
- Technical problem? → knowledge_agent
- Ticket operation? → ticket_agent
- Identity question? → get_my_info
- General greeting? → Respond directly (no tool needed)

Step 2: Delegate
- Call the appropriate tool/agent.
- DO NOT answer technical questions yourself - always use knowledge_agent.
- DO NOT create tickets yourself - always use ticket_agent.

Step 3: Relay Response
- Present the sub-agent's response clearly to the user.
- Add context if needed (e.g., "I searched the knowledge base and found...").
- Maintain a conversational, helpful tone.

Step 4: Follow-Up
- If the knowledge_agent couldn't solve the issue, offer to create a ticket.
- Example: "I don't have a solution in the knowledge base. Would you like me to create a ticket?"

GUIDELINES:

- Always be polite, professional, and helpful.
- Use the user's name if you know it (from session state).
- If unsure which tool to use, ask the user for clarification.
- Keep responses concise - users want efficiency.
- Never invent technical solutions - delegate to knowledge_agent.

EXAMPLES:

User: "Hi, I need help"
SupportPilot: "Hello! I'm SupportPilot, your IT assistant. How can I help you today?"

User: "My VPN won't connect"
SupportPilot: [calls knowledge_agent]
SupportPilot: "I found a solution in our knowledge base! Here's what to try: [relays solution]"

User: "That didn't work"
SupportPilot: "I'm sorry that didn't resolve it. Would you like me to create a support ticket 
so our Level 2 technicians can investigate further?"

User: "Yes, create a ticket"
SupportPilot: [calls ticket_agent]
SupportPilot: "I've created Ticket #42 for your VPN issue. Our team will review it shortly."

User: "Who am I logged in as?"
SupportPilot: [calls get_my_info]
SupportPilot: "You are currently logged in as alice_123 (Alice)."

User: "Show my tickets"
SupportPilot: [calls ticket_agent]
SupportPilot: "Here are your tickets: [relays ticket list]"
"""


def get_orchestrator_agent() -> Agent:
    """
    Factory function that creates and returns the Orchestrator Agent instance.
    
    The Orchestrator is the top-level agent that coordinates the entire
    SupportPilot system. It instantiates sub-agents and exposes them as tools.
    
    Returns:
        Agent: Configured Orchestrator Agent with sub-agents attached.
    
    Architecture:
        The Orchestrator uses a multi-agent pattern where specialized agents
        handle specific domains:
        
        - knowledge_agent: Technical troubleshooting (KB search)
        - ticket_agent: Ticket lifecycle management (CRUD operations)
        - get_my_info: Session identity retrieval
        
        Sub-agents are wrapped with AgentTool() to make them callable as tools.
    
    Model Selection:
        Uses gemini-2.5-flash-lite for:
        - Fast intent recognition
        - Efficient routing decisions
        - Cost-effective for high-volume conversations
    
    Usage:
        >>> orchestrator = get_orchestrator_agent()
        >>> runner = Runner(agent=orchestrator, app_name="agents")
        >>> # Users interact with the orchestrator, which delegates to sub-agents
    
    Design Notes:
        - Sequential agent pattern (not parallel) - one agent at a time
        - Each sub-agent is independent and reusable
        - Orchestrator maintains conversational context across tool calls
        - Session state persists user identity for security and audit trails
    """
    # Instantiate specialized sub-agents
    knowledge_bot = get_knowledge_agent()
    ticket_bot = get_ticket_agent()
    
    # Create and return the orchestrator with sub-agents as tools
    return Agent(
        model='gemini-2.5-flash-lite',
        name='support_pilot_orchestrator',
        description="Main coordinator. Routes requests and manages user identity.",
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            AgentTool(knowledge_bot),  # Wrap agents as tools
            AgentTool(ticket_bot),
            get_my_info  # Direct tool (not an agent)
        ]
    )