"""
Query Agent - Ticket Status Specialist

This agent handles user requests to check their support ticket status.
Provides clear, formatted information about open and closed tickets.
"""

import os
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from src.core.observability import logger
from src.tools.support_tools import execute_tool


class QueryAgent:
    """
    Specialized agent for querying ticket status.
    
    This agent:
    1. Receives user ID from Orchestrator
    2. Retrieves all user's tickets
    3. Formats ticket information clearly for user
    
    Attributes:
        client: Google GenAI client
        model_name: LLM model to use
        system_prompt: Loaded from prompts/query_agent.prompt
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Query Agent.
        
        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)
        
        # Load system prompt
        self.system_prompt = self._load_prompt()
        
        # Define tools available to this agent
        self.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="get_ticket_status",
                        description=(
                            "Retrieve all support tickets for a specific user. "
                            "Returns ticket details including status, description, and timestamps."
                        ),
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "user_id": types.Schema(
                                    type=types.Type.STRING,
                                    description="User identifier to query tickets for"
                                )
                            },
                            required=["user_id"]
                        )
                    )
                ]
            )
        ]
        
        logger.info("query_agent_initialized", model=model_name)
    
    def _load_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_path = "prompts/query_agent.prompt"
        
        try:
            with open(prompt_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback inline prompt
            return """You are a Ticket Status Specialist.

Your job is to retrieve and present ticket information clearly to users.

WORKFLOW:
1. Use get_ticket_status tool with the user_id provided
2. Format the results in a clear, user-friendly way
3. Explain what each status means

RULES:
- Present tickets in a clean, organized format
- Use status indicators (🔴 Open, 🟡 In Progress, 🟢 Closed)
- Show most recent tickets first
- Explain status meanings briefly
- If no tickets, be helpful and offer assistance

FORMAT (tickets found):
"Here are your support tickets:

🔴 TICKET-1001 - Open
   Issue: VPN connection problems
   Created: Nov 15, 2025
   Status: Awaiting assignment

🟢 TICKET-0995 - Closed
   Issue: Password reset
   Created: Nov 14, 2025
   Resolved: Nov 14, 2025

Need help with anything else?"

FORMAT (no tickets):
"You don't have any support tickets at the moment.

If you're experiencing any IT issues, I'm here to help! Just describe the problem."
"""
    
    def query_tickets(self, user_id: str, trace_id: str) -> Dict[str, Any]:
        """
        Query all tickets for a user.
        
        Args:
            user_id: User identifier
            trace_id: Trace ID for observability
            
        Returns:
            Dict containing:
                - success (bool): Whether query succeeded
                - count (int): Number of tickets found
                - response (str): Formatted response for user
        """
        logger.info(
            "query_agent_querying",
            trace_id=trace_id,
            user_id=user_id
        )
        
        message = f"""User ID: {user_id}

Please retrieve and present this user's support tickets."""
        
        try:
            # Call LLM with tool access
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=message)]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    tools=self.tools,
                    temperature=0.3,  # Low temp for consistent formatting
                )
            )
            
            # Process response
            result = self._process_response(response, trace_id)
            
            logger.info(
                "query_agent_completed",
                trace_id=trace_id,
                success=result["success"],
                ticket_count=result.get("count", 0)
            )
            
            return result
            
        except Exception as e:
            logger.error("query_agent_error", trace_id=trace_id, error=str(e))
            return {
                "success": False,
                "count": 0,
                "response": "I encountered an error retrieving your tickets. Please try again."
            }
    
    def _process_response(self, response: types.GenerateContentResponse, trace_id: str) -> Dict[str, Any]:
        """
        Process LLM response and execute ticket query tool.
        
        Args:
            response: LLM response
            trace_id: Trace ID
            
        Returns:
            Dict with query result
        """
        if not response.candidates:
            return {
                "success": False,
                "count": 0,
                "response": "Unable to retrieve tickets at this time."
            }
        
        candidate = response.candidates[0]
        
        text_parts = []
        query_result = None
        
        for part in candidate.content.parts:
            if part.text:
                text_parts.append(part.text)
            
            elif part.function_call:
                # Execute get_ticket_status tool
                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args)
                
                logger.info(
                    "query_agent_tool_call",
                    trace_id=trace_id,
                    tool=tool_name,
                    user_id=tool_args.get("user_id")
                )
                
                query_result = execute_tool(tool_name, tool_args)
        
        # Combine response
        full_text = "\n".join(text_parts)
        
        if query_result is not None:
            return {
                "success": True,
                "count": query_result.get("count", 0),
                "response": full_text if full_text else self._format_tickets(query_result)
            }
        else:
            return {
                "success": False,
                "count": 0,
                "response": full_text if full_text else "No tickets found."
            }
    
    def _format_tickets(self, query_result: Dict[str, Any]) -> str:
        """
        Fallback formatting if LLM doesn't format properly.
        
        Args:
            query_result: Result from get_ticket_status tool
            
        Returns:
            str: Formatted ticket list
        """
        if not query_result.get("found"):
            return "You don't have any support tickets at the moment."
        
        tickets = query_result.get("tickets", [])
        output = [f"You have {len(tickets)} ticket(s):\n"]
        
        for ticket in tickets:
            status = ticket["status"]
            emoji = "🔴" if status == "Open" else "🟡" if status == "In Progress" else "🟢"
            
            output.append(f"{emoji} {ticket['ticket_id']} - {status}")
            output.append(f"   Issue: {ticket['description']}")
            output.append(f"   Created: {ticket['created_at']}")
            output.append("")
        
        return "\n".join(output)