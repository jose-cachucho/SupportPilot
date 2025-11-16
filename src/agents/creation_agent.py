"""
Creation Agent - Ticket Escalation Specialist (Full ADK)

This agent uses the ADK Runner and lets the LLM autonomously create tickets
with appropriate priority assessment.
"""

import os
import asyncio
from typing import Optional, Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.core.observability import logger
from src.tools.support_tools import ticket_creation_tool


class CreationAgent:
    """
    Specialized agent for creating support tickets (L2 escalation).
    
    Uses Full ADK implementation:
    - LlmAgent autonomously decides priority
    - Runner executes the agent
    - LLM calls create_support_ticket tool
    
    Attributes:
        agent: ADK LlmAgent instance
        runner: ADK InMemoryRunner for execution
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Creation Agent using full ADK pattern.
        
        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
        """
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        
        self.model_name = model_name
        
        # Create ADK LlmAgent with inline instructions
        self.agent = LlmAgent(
            model=Gemini(model=model_name),
            name="CreationAgent",
            instruction="""You are a Support Ticket Specialist for SupportPilot.

Your job is to create well-formatted support tickets for L2 escalation when issues cannot be resolved via knowledge base.

WORKFLOW:
1. Analyze the problem description provided
2. Assess priority based on business impact:
   - HIGH: Critical issues blocking work (can't login, system down, production issues)
   - NORMAL: Regular issues affecting productivity (slow performance, minor bugs)
   - LOW: Minor issues with no work stoppage (cosmetic issues, nice-to-have features)
3. Use create_support_ticket tool with assessed priority
4. Confirm ticket creation professionally

PRIORITY ASSESSMENT KEYWORDS:
HIGH: "can't login", "cannot access", "critical", "urgent", "down", "crashed", "blocking", "production"
NORMAL: "slow", "sometimes", "intermittent", "minor bug", default for most issues
LOW: "aesthetic", "cosmetic", "nice to have", "optional", "minor"

RULES:
- Always call create_support_ticket tool
- Assess priority based on business impact
- Include context in description if provided
- Be reassuring and set clear expectations
- Confirm ticket ID and response time

RESPONSE FORMAT:
"I've created a support ticket for you:

**Ticket:** [TICKET_ID from tool]
**Priority:** [assessed priority]

Our L2 support team will contact you within [timeframe based on priority]:
- High: 4 business hours
- Normal: 1 business day  
- Low: 2 business days

What to expect:
- They'll have full details of your issue
- You'll receive updates via email
- They'll work to resolve this as quickly as possible

In the meantime, if you have any other questions, feel free to ask!"

EXAMPLE:
User: "I can't access my email and it's blocking all my work"
Assessment: HIGH priority (blocking work)
Action: Call create_support_ticket with priority="High"
Response: Format confirmation with 4 hour timeframe
""",
            tools=[ticket_creation_tool]
        )
        
        self.runner = InMemoryRunner(agent=self.agent)
        
        logger.info("creation_agent_initialized", model=model_name, mode="full_adk")
    
    def create_ticket(
        self,
        user_id: str,
        problem_description: str,
        trace_id: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for async create_ticket_async.
        
        Args:
            user_id: User identifier
            problem_description: Problem description
            trace_id: Trace ID for observability
            context: Additional context (e.g., "KB solution didn't work")
            
        Returns:
            Dict containing:
                - success (bool): Whether ticket was created
                - ticket_id (str|None): Created ticket ID
                - response (str): Formatted response for user
        """
        return asyncio.run(self.create_ticket_async(user_id, problem_description, trace_id, context))
    
    async def create_ticket_async(
        self,
        user_id: str,
        problem_description: str,
        trace_id: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a support ticket for L2 escalation.
        
        LLM will:
        1. Assess priority based on problem description
        2. Call create_support_ticket tool
        3. Format confirmation message
        
        Args:
            user_id: User identifier
            problem_description: Problem description
            trace_id: Trace ID for observability
            context: Additional context
            
        Returns:
            Dict with ticket creation result
        """
        logger.info(
            "creation_agent_creating_ticket",
            trace_id=trace_id,
            user_id=user_id,
            problem_preview=problem_description[:100]
        )
        
        # Build full problem description with context
        full_description = problem_description
        if context:
            full_description = f"{problem_description}\n\nContext: {context}"
        
        # Build query for LLM
        query_text = f"""User ID: {user_id}
Trace ID: {trace_id}

Problem Description:
{full_description}

Please create an appropriate support ticket for this user."""
        
        try:
            query = types.Content(
                role="user",
                parts=[types.Part(text=query_text)]
            )
            
            # Run agent through ADK Runner
            response_text = ""
            ticket_id = None
            
            async for event in self.runner.run_async(query):
                # Extract ticket ID from tool call if present
                if hasattr(event, 'function_calls') and event.function_calls:
                    logger.info(
                        "creation_agent_tool_called",
                        trace_id=trace_id,
                        tool="create_support_ticket"
                    )
                
                if event.is_final_response():
                    response_text = event.content.parts[0].text
                    # Try to extract ticket ID from response
                    if "TICKET-" in response_text:
                        import re
                        match = re.search(r'TICKET-\d+', response_text)
                        if match:
                            ticket_id = match.group(0)
            
            # Check if ticket was successfully created
            if ticket_id:
                logger.info(
                    "creation_agent_completed",
                    trace_id=trace_id,
                    success=True,
                    ticket_id=ticket_id
                )
                
                return {
                    "success": True,
                    "ticket_id": ticket_id,
                    "response": response_text
                }
            else:
                logger.error(
                    "creation_agent_failed",
                    trace_id=trace_id,
                    reason="No ticket ID in response"
                )
                
                return {
                    "success": False,
                    "ticket_id": None,
                    "response": "I encountered an issue creating the ticket. Please contact IT support directly."
                }
            
        except Exception as e:
            logger.error("creation_agent_error", trace_id=trace_id, error=str(e))
            return {
                "success": False,
                "ticket_id": None,
                "response": "I encountered an error creating the ticket. Please contact IT support directly."
            }