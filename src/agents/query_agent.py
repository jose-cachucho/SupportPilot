"""
Query Agent - Ticket Status Specialist (Full ADK)

This agent uses the ADK Runner to retrieve and present ticket status information.
"""

import os
import asyncio
from typing import Optional, Dict, Any

from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import InMemoryRunner
from google.genai import types

from src.core.observability import logger
from src.tools.support_tools import ticket_query_tool


class QueryAgent:
    """
    Specialized agent for querying ticket status.
    
    Uses Full ADK implementation:
    - LlmAgent autonomously formats ticket information
    - Runner executes the agent
    - LLM calls get_ticket_status tool
    
    Attributes:
        agent: ADK LlmAgent instance
        runner: ADK InMemoryRunner for execution
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Query Agent using full ADK pattern.
        
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
            name="QueryAgent",
            instruction="""You are a Ticket Status Specialist for SupportPilot.

Your job is to retrieve and present support ticket information clearly to users.

WORKFLOW:
1. ALWAYS use the get_ticket_status tool with the user_id provided
2. Format the results in a clear, user-friendly way
3. Use status emojis for visual clarity
4. Explain what each status means briefly

STATUS INDICATORS (use emojis):
- 🔴 Open: Ticket created, awaiting assignment to support staff
- 🟡 In Progress: Support engineer is actively working on the issue
- 🟢 Closed: Issue has been resolved

RULES:
- Always call get_ticket_status tool first
- Present tickets in a clean, organized format
- Show most recent tickets first
- Use emojis for quick visual scanning
- Include ticket ID, description, status, and creation date
- If no tickets found, be helpful and offer assistance
- Do NOT make up ticket information
- Do NOT promise specific resolution times

RESPONSE FORMAT (when tickets found):
"Here are your support tickets ([count] total):

🔴 **TICKET-1001** - Open
   Issue: VPN connection problems
   Created: Nov 15, 2025 at 10:30 AM
   → Awaiting assignment to support engineer

🟡 **TICKET-0998** - In Progress
   Issue: Email sync issues on mobile
   Created: Nov 14, 2025 at 2:15 PM
   → Being actively worked on

🟢 **TICKET-0995** - Closed
   Issue: Password reset request
   Created: Nov 14, 2025 at 9:00 AM
   Resolved: Nov 14, 2025 at 9:05 AM

Need help with anything else?"

RESPONSE FORMAT (when no tickets):
"You don't have any support tickets at the moment.

If you're experiencing any IT issues, I'm here to help! Just describe the problem and I'll do my best to assist you."

STATUS EXPLANATIONS:
- Open: "Your ticket is in the queue and will be picked up by the next available support engineer."
- In Progress: "A support engineer is actively working on your issue. You should receive an update soon."
- Closed: "This issue has been marked as resolved. If the problem persists, let me know and I can create a new ticket."

EXAMPLE:
User: "What are my tickets?"
Action: Call get_ticket_status(user_id)
Response: Format all tickets with emojis and details as shown above
""",
            tools=[ticket_query_tool]
        )
        
        self.runner = InMemoryRunner(agent=self.agent)
        
        logger.info("query_agent_initialized", model=model_name, mode="full_adk")
    
    def query_tickets(self, user_id: str, trace_id: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for async query_tickets_async.
        
        Args:
            user_id: User identifier
            trace_id: Trace ID for observability
            
        Returns:
            Dict containing:
                - success (bool): Whether query succeeded
                - count (int): Number of tickets found
                - response (str): Formatted response for user
        """
        return asyncio.run(self.query_tickets_async(user_id, trace_id))
    
    async def query_tickets_async(self, user_id: str, trace_id: str) -> Dict[str, Any]:
        """
        Query all tickets for a user.
        
        LLM will:
        1. Call get_ticket_status tool
        2. Format results with emojis and details
        3. Provide status explanations
        
        Args:
            user_id: User identifier
            trace_id: Trace ID for observability
            
        Returns:
            Dict with query result
        """
        logger.info(
            "query_agent_querying",
            trace_id=trace_id,
            user_id=user_id
        )
        
        # Build query for LLM
        query_text = f"""User ID: {user_id}

Please retrieve and present this user's support tickets."""
        
        try:
            query = types.Content(
                role="user",
                parts=[types.Part(text=query_text)]
            )
            
            # Run agent through ADK Runner
            response_text = ""
            ticket_count = 0
            
            async for event in self.runner.run_async(query):
                # Track if tool was called
                if hasattr(event, 'function_calls') and event.function_calls:
                    logger.info(
                        "query_agent_tool_called",
                        trace_id=trace_id,
                        tool="get_ticket_status"
                    )
                
                if event.is_final_response():
                    response_text = event.content.parts[0].text
                    # Try to count tickets from response
                    import re
                    tickets_found = re.findall(r'TICKET-\d+', response_text)
                    ticket_count = len(tickets_found)
            
            logger.info(
                "query_agent_completed",
                trace_id=trace_id,
                success=True,
                ticket_count=ticket_count
            )
            
            return {
                "success": True,
                "count": ticket_count,
                "response": response_text
            }
            
        except Exception as e:
            logger.error("query_agent_error", trace_id=trace_id, error=str(e))
            return {
                "success": False,
                "count": 0,
                "response": "I encountered an error retrieving your tickets. Please try again."
            }