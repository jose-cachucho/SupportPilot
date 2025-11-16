"""
Creation Agent - Ticket Escalation Specialist

This agent is responsible for creating support tickets when issues cannot
be resolved via knowledge base. It formats ticket information professionally.
"""

import os
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from src.core.observability import logger
from src.tools.support_tools import execute_tool


class CreationAgent:
    """
    Specialized agent for creating support tickets (L2 escalation).
    
    This agent:
    1. Receives problem details and user info from Orchestrator
    2. Creates a properly formatted support ticket
    3. Returns ticket confirmation to user
    
    Attributes:
        client: Google GenAI client
        model_name: LLM model to use
        system_prompt: Loaded from prompts/creation_agent.prompt
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Creation Agent.
        
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
                        name="create_support_ticket",
                        description=(
                            "Create a support ticket for L2 escalation. "
                            "Use this to escalate issues that cannot be resolved via knowledge base."
                        ),
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "user_id": types.Schema(
                                    type=types.Type.STRING,
                                    description="User identifier"
                                ),
                                "description": types.Schema(
                                    type=types.Type.STRING,
                                    description="Detailed problem description"
                                ),
                                "priority": types.Schema(
                                    type=types.Type.STRING,
                                    description="Priority: Low, Normal, or High",
                                    enum=["Low", "Normal", "High"]
                                ),
                                "trace_id": types.Schema(
                                    type=types.Type.STRING,
                                    description="Trace ID for observability"
                                )
                            },
                            required=["user_id", "description"]
                        )
                    )
                ]
            )
        ]
        
        logger.info("creation_agent_initialized", model=model_name)
    
    def _load_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_path = "prompts/creation_agent.prompt"
        
        try:
            with open(prompt_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback inline prompt
            return """You are a Support Ticket Specialist.

Your job is to create well-formatted support tickets for L2 escalation.

WORKFLOW:
1. Analyze the problem description provided
2. Determine appropriate priority (Low/Normal/High) based on:
   - Low: Minor issues, no work stoppage
   - Normal: Regular issues affecting productivity
   - High: Critical issues blocking work completely
3. Use create_support_ticket tool with:
   - user_id (provided)
   - description (clear summary including context)
   - priority (your assessment)
   - trace_id (provided)
4. Confirm ticket creation to user professionally

RULES:
- Always assess priority appropriately
- Include context in description (what was already tried if mentioned)
- Be reassuring and professional
- Provide clear expectations about response time

FORMAT:
"I've created a support ticket for you:

Ticket: [TICKET_ID]
Priority: [PRIORITY]

Our L2 support team will contact you within [TIMEFRAME].

In the meantime, if you have any other questions, feel free to ask!"
"""
    
    def create_ticket(
        self,
        user_id: str,
        problem_description: str,
        trace_id: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a support ticket for L2 escalation.
        
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
        
        # Prepare message for LLM
        message = f"""User ID: {user_id}
Trace ID: {trace_id}

Problem Description:
{full_description}

Please create an appropriate support ticket for this user."""
        
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
                    temperature=0.5,
                )
            )
            
            # Process response
            result = self._process_response(response, trace_id)
            
            logger.info(
                "creation_agent_completed",
                trace_id=trace_id,
                success=result["success"],
                ticket_id=result.get("ticket_id")
            )
            
            return result
            
        except Exception as e:
            logger.error("creation_agent_error", trace_id=trace_id, error=str(e))
            return {
                "success": False,
                "ticket_id": None,
                "response": "I encountered an error creating the ticket. Please contact IT support directly."
            }
    
    def _process_response(self, response: types.GenerateContentResponse, trace_id: str) -> Dict[str, Any]:
        """
        Process LLM response and execute ticket creation tool.
        
        Args:
            response: LLM response
            trace_id: Trace ID
            
        Returns:
            Dict with ticket creation result
        """
        if not response.candidates:
            return {
                "success": False,
                "ticket_id": None,
                "response": "Unable to create ticket at this time."
            }
        
        candidate = response.candidates[0]
        
        text_parts = []
        ticket_result = None
        
        for part in candidate.content.parts:
            if part.text:
                text_parts.append(part.text)
            
            elif part.function_call:
                # Execute create_support_ticket tool
                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args)
                
                logger.info(
                    "creation_agent_tool_call",
                    trace_id=trace_id,
                    tool=tool_name,
                    user_id=tool_args.get("user_id"),
                    priority=tool_args.get("priority")
                )
                
                ticket_result = execute_tool(tool_name, tool_args)
        
        # Combine response
        full_text = "\n".join(text_parts)
        
        if ticket_result and ticket_result.get("success"):
            return {
                "success": True,
                "ticket_id": ticket_result["ticket_id"],
                "response": full_text if full_text else ticket_result["message"]
            }
        else:
            return {
                "success": False,
                "ticket_id": None,
                "response": full_text if full_text else "Failed to create ticket."
            }