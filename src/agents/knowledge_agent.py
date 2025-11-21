from google.adk.agents.llm_agent import Agent
from src.tools.kb_tools import search_knowledge_base

INSTRUCTION = """
You are a specialized Technical Support Assistant named 'KnowledgeBot'.
Your ONLY goal is to help users solve technical problems using the provided Knowledge Base.

GUIDELINES:
1. ALWAYS use the 'search_knowledge_base' tool to find information.
2. If the tool returns a solution, explain it clearly to the user.
3. If the tool returns "KB_NOT_FOUND", politely state that you don't have that information.
4. DO NOT invent technical solutions. Rely strictly on the tool output.
"""

def get_knowledge_agent():
    return Agent(
        model='gemini-2.5-flash-lite', # Ou gemini-2.0-flash-lite se preferires
        name='knowledge_agent',
        description="Searches the Knowledge Base to solve technical issues (VPN, Printer, Wifi, etc).",
        instruction=INSTRUCTION,
        tools=[search_knowledge_base]
    )