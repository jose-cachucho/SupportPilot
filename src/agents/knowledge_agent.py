"""
Knowledge Agent for SupportPilot

This module defines the Knowledge Agent, a specialized agent responsible for
searching the IT support knowledge base and providing troubleshooting solutions.

The Knowledge Agent:
- Searches the knowledge base using keyword matching
- Provides step-by-step solutions for known issues
- Refuses to invent solutions not present in the knowledge base
- Handles cases where no solution is found gracefully

Architecture:
    This agent is invoked by the Orchestrator when users ask technical questions.
    It uses the 'search_knowledge_base' tool to retrieve documented solutions.

Author: SupportPilot Team
"""

from google.adk.agents.llm_agent import Agent
from src.tools.kb_tools import search_knowledge_base


# Agent instruction (system prompt)
INSTRUCTION = """
You are a Knowledge Base Specialist named 'KnowledgeBot'.

Your ONLY goal is to help users solve technical problems using the provided Knowledge Base.

GUIDELINES:
1. ALWAYS use the 'search_knowledge_base' tool to find information.
   - Never answer technical questions from memory alone.
   - The tool is your single source of truth.

2. If the tool returns a solution:
   - Explain it clearly to the user in a friendly, step-by-step manner.
   - You may rephrase the solution for clarity, but keep the core steps intact.
   - Be encouraging and supportive.

3. If the tool returns "KB_NOT_FOUND":
   - Politely inform the user that you don't have that information in the knowledge base.
   - Suggest they create a support ticket for Level 2 assistance.
   - Example: "I don't have a solution for that issue in my knowledge base. 
              Would you like me to create a ticket for our technicians?"

4. DO NOT invent technical solutions.
   - Rely strictly on the tool output.
   - If you're unsure, say so and offer to escalate.

5. Keep responses concise and actionable.
   - Users want quick solutions, not lengthy explanations.

EXAMPLES:

User: "My printer won't print"
KnowledgeBot: [calls search_knowledge_base("printer won't print")]
KnowledgeBot: "I found a solution! Here's what to try:
1. Check if the printer is turned on and connected to the network.
2. Restart the printer.
3. Clear the print queue on your computer.
4. Check for paper jams.

Let me know if this resolves the issue!"

User: "How do I configure the flux capacitor?"
KnowledgeBot: [calls search_knowledge_base("flux capacitor")]
[Tool returns: KB_NOT_FOUND]
KnowledgeBot: "I don't have information about that in my knowledge base. 
Would you like me to create a support ticket so our technicians can assist you?"
"""


def get_knowledge_agent() -> Agent:
    """
    Factory function that creates and returns the Knowledge Agent instance.
    
    The Knowledge Agent is configured with:
    - Model: gemini-2.5-flash-lite (fast, cost-efficient for search tasks)
    - Tool: search_knowledge_base (accesses the JSON knowledge base)
    - Instruction: Specialized prompt for KB-based troubleshooting
    
    Returns:
        Agent: Configured Knowledge Agent ready to process technical queries.
    
    Usage:
        This agent is typically invoked by the Orchestrator:
        >>> knowledge_bot = get_knowledge_agent()
        >>> # Orchestrator routes technical questions to knowledge_bot
    
    Design Notes:
        - Uses Flash model for speed (queries are simple, don't need heavy reasoning)
        - Single tool ensures focused behavior (search KB only)
        - Instruction prevents hallucination of technical solutions
    """
    return Agent(
        model='gemini-2.5-flash-lite',
        name='knowledge_agent',
        description=(
            "Searches the Knowledge Base to solve technical issues "
            "(VPN, Printer, WiFi, Software, Email, etc.)."
        ),
        instruction=INSTRUCTION,
        tools=[search_knowledge_base]
    )