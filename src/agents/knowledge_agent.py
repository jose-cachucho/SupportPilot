"""
Knowledge Agent - L1 Support Specialist (Full ADK Implementation)

This version properly uses ADK Runner and lets the LLM decide when to use tools.
System prompt is inline (like in the course examples) for simplicity.
"""

import os
import asyncio
from typing import Optional, Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.core.observability import logger
from src.tools.support_tools import kb_search_tool


class KnowledgeAgent:
    """
    Specialized agent for L1 support resolution using knowledge base.
    
    This is the PROPER ADK implementation where:
    - LlmAgent has access to tools
    - Runner executes the agent
    - LLM DECIDES when to call search_knowledge_base
    - System prompt is inline (like currency_agent example from course)
    
    Attributes:
        agent: ADK LlmAgent instance
        runner: ADK InMemoryRunner for execution
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Knowledge Agent using full ADK pattern.
        
        Args:
            api_key: Google AI API key (set as env var for ADK)
            model_name: Gemini model to use
        """
        # Set API key as environment variable (required by ADK)
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        
        self.model_name = model_name
        
        # Create ADK LlmAgent with tool access and instructions
        # Instructions are inline (like in the course examples)
        self.agent = LlmAgent(
            model=Gemini(model=model_name),
            name="KnowledgeAgent",
            instruction="""You are a Level 1 IT Support Specialist for SupportPilot.

Your ONLY job is to search the knowledge base and provide solutions to technical problems.

WORKFLOW:
1. ALWAYS use the search_knowledge_base tool first with the user's problem description
2. If solution found: Present it clearly with the article title and numbered steps
3. If NOT found: Return EXACTLY "KB_NOT_FOUND" (nothing else)

RULES:
- You MUST call search_knowledge_base before responding
- Present solutions in clear, numbered steps
- Be professional but friendly
- If no solution exists in KB, return only "KB_NOT_FOUND"
- NEVER make up solutions - only use content from the knowledge base
- End with "Let me know if this resolves your issue!"

EXAMPLE (solution found):
"I found a solution for this issue:

**VPN Connection Issues**

Steps:
1. Check your internet connection is working
2. Restart your router/modem
3. Close and reopen the VPN client application
4. Verify your VPN credentials are correct

Let me know if this resolves your issue!"

EXAMPLE (not found):
"KB_NOT_FOUND"
""",
            tools=[kb_search_tool]  # Tool that LLM can autonomously use
        )
        
        # Create InMemoryRunner for agent execution
        self.runner = InMemoryRunner(agent=self.agent)
        
        logger.info("knowledge_agent_initialized", model=model_name, mode="full_adk")
    
    def resolve(self, problem_description: str, trace_id: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for async resolve_async.
        
        For CLI/testing convenience. Internally calls the async version.
        
        Args:
            problem_description: User's problem description
            trace_id: Trace ID for observability
            
        Returns:
            Dict containing:
                - success (bool): Whether solution was found
                - response (str): Formatted response for user
                - article_id (str|None): KB article used (if found)
        """
        # Run async version in event loop
        return asyncio.run(self.resolve_async(problem_description, trace_id))
    
    async def resolve_async(self, problem_description: str, trace_id: str) -> Dict[str, Any]:
        """
        Attempt to resolve a technical problem using the knowledge base.
        
        This is the PROPER ADK way:
        - Create Content from user message
        - Let Runner execute the agent
        - LLM autonomously decides to call search_knowledge_base
        - Parse response from events
        
        Args:
            problem_description: User's problem description
            trace_id: Trace ID for observability
            
        Returns:
            Dict containing:
                - success (bool): Whether solution was found
                - response (str): Formatted response for user
                - article_id (str|None): KB article used (if found)
        """
        logger.info(
            "knowledge_agent_resolving",
            trace_id=trace_id,
            problem_preview=problem_description[:100]
        )
        
        try:
            # Create message content for ADK
            query = types.Content(
                role="user",
                parts=[types.Part(text=problem_description)]
            )
            
            # Run agent through ADK Runner
            # The LLM will autonomously decide to call search_knowledge_base
            response_text = ""
            tool_called = False
            
            async for event in self.runner.run_async(query):
                # Track if tool was called
                if hasattr(event, 'function_calls') and event.function_calls:
                    tool_called = True
                    logger.info(
                        "knowledge_agent_tool_called",
                        trace_id=trace_id,
                        tool="search_knowledge_base"
                    )
                
                # Get final response
                if event.is_final_response():
                    response_text = event.content.parts[0].text
            
            # Parse response to determine success
            if "KB_NOT_FOUND" in response_text:
                logger.info(
                    "knowledge_agent_completed",
                    trace_id=trace_id,
                    success=False,
                    reason="No KB solution found",
                    tool_called=tool_called
                )
                
                return {
                    "success": False,
                    "response": "KB_NOT_FOUND",
                    "article_id": None
                }
            else:
                logger.info(
                    "knowledge_agent_completed",
                    trace_id=trace_id,
                    success=True,
                    tool_called=tool_called
                )
                
                return {
                    "success": True,
                    "response": response_text,
                    "article_id": "determined_by_llm"  # LLM handles formatting
                }
            
        except Exception as e:
            logger.error("knowledge_agent_error", trace_id=trace_id, error=str(e))
            return {
                "success": False,
                "response": "I encountered an error searching the knowledge base.",
                "article_id": None
            }