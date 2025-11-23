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
                      ↘ get_my_info (identity management)

    The Orchestrator uses ADK's AgentTool to invoke sub-agents dynamically
    based on user intent. All tools and agents return structured dictionaries
    for reliable communication.

Author: SupportPilot Team
"""

from google.adk.agents.llm_agent import LlmAgent
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
   - Use for ALL ticket-related operations.
   - Examples: 
     * "Create a ticket"
     * "What's my ticket status?"
     * "Show all tickets"
     * "What is the status of ticket 5?" ← IMPORTANT: Use this for specific ticket queries
     * "Close ticket 5"
     * "List all tickets"
   - This agent has specialized tools for:
     * Viewing specific tickets by ID
     * Listing all system tickets (service_desk_agent only)
     * Creating and updating tickets
   - IMPORTANT: Simply forward the user's request to ticket_agent. Don't try to answer ticket questions yourself.

3. get_my_info:
   - Use if the user asks who they are or requests their user information.
   - IMPORTANT: You MUST explicitly tell the user their ID, Name, and Role returned by this tool.
   - Don't stay silent after calling this tool - communicate the result!
   - Example: "You are logged in as alice_123 (End User)."

ROUTING LOGIC:

Step 1: Identify Intent
- Technical problem? → knowledge_agent
- ANY ticket question/operation? → ticket_agent (including "status of ticket X", "show tickets", etc.)
- Identity question? → get_my_info
- General greeting? → Respond directly (no tool needed)

Step 2: Delegate
- Call the appropriate tool/agent.
- DO NOT answer technical questions yourself - always use knowledge_agent.
- DO NOT answer ticket questions yourself - always use ticket_agent.
- DO NOT make assumptions about permissions - let ticket_agent enforce RBAC.

Step 3: Relay Response
- Present the sub-agent's response clearly to the user.
- Add context if needed (e.g., "I searched the knowledge base and found...").
- Maintain a conversational, helpful tone.

Step 4: Follow-Up
- If the knowledge_agent couldn't solve the issue, offer to create a ticket.
- Example: "I don't have a solution in the knowledge base. Would you like me to create a ticket?"

CRITICAL RULES:

- NEVER make assumptions about user permissions or roles.
- ALWAYS delegate ticket operations to ticket_agent (it handles RBAC internally).
- If unsure whether a query is about tickets, default to calling ticket_agent.
- Do NOT respond with generic messages like "I can only show your own tickets" - 
  let ticket_agent handle that based on the user's actual role.

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
SupportPilot: "You are currently logged in as alice_123 (End User)."

User: "Show my tickets"
SupportPilot: [calls ticket_agent]
SupportPilot: [relays ticket_agent response]

User: "What is the status of ticket 5?"
SupportPilot: [calls ticket_agent]
SupportPilot: [relays ticket_agent response - ticket_agent will handle RBAC]

User (service_desk_agent): "Show all tickets"
SupportPilot: [calls ticket_agent]
SupportPilot: [relays ticket_agent response - ticket_agent knows user is service_desk_agent]
"""

def get_orchestrator_agent() -> LlmAgent:
    """
    Factory function that creates and returns the Orchestrator Agent instance.
    
    The Orchestrator is the top-level agent that coordinates the entire
    SupportPilot system. It instantiates sub-agents and exposes them as tools
    using AgentTool.
    
    Returns:
        LlmAgent: Configured Orchestrator Agent with sub-agents attached.
    
    Architecture:
        The Orchestrator uses a multi-agent pattern where specialized agents
        handle specific domains:
        
        - knowledge_agent: Technical troubleshooting (KB search)
        - ticket_agent: Ticket lifecycle management (CRUD operations)
        - get_my_info: Session identity retrieval
        
        Sub-agents are wrapped with AgentTool() to make them callable as tools.
        All agents and tools return structured dictionaries for reliable communication.
    
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
        - All communication uses structured dictionaries (ADK best practice)
    """
    # Instantiate specialized sub-agents
    knowledge_bot = get_knowledge_agent()
    ticket_bot = get_ticket_agent()
    
    # Create and return the orchestrator with sub-agents wrapped as AgentTools
    return LlmAgent(
        model='gemini-2.5-flash-lite', 
        name='support_pilot_orchestrator',
        description="Main coordinator. Routes requests and manages user identity.",
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[
            AgentTool(knowledge_bot),  # Wrap agents with AgentTool
            AgentTool(ticket_bot),
            get_my_info  # Direct tool (not an agent)
        ]
    )