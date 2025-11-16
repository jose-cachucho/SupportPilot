"""
Knowledge Agent - L1 Support Specialist

This agent is responsible for resolving technical issues using the knowledge base.
It has access to search_knowledge_base tool and returns structured solutions.
"""

import os
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from src.core.observability import logger
from src.tools.support_tools import execute_tool


class KnowledgeAgent:
    """
    Specialized agent for L1 support resolution using knowledge base.
    
    This agent:
    1. Receives a problem description from Orchestrator
    2. Searches the knowledge base
    3. Returns formatted solution or indicates failure
    
    Attributes:
        client: Google GenAI client
        model_name: LLM model to use
        system_prompt: Loaded from prompts/knowledge_agent.prompt
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Knowledge Agent.
        
        Args:
            api_key: Google AI API key
            model_name: Gemini model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)
        
        # Load system prompt from file
        self.system_prompt = self._load_prompt()
        
        # Define tools available to this agent
        self.tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name="search_knowledge_base",
                        description=(
                            "Search the IT support knowledge base for solutions to technical problems. "
                            "Returns step-by-step solutions if found, or indicates no solution available."
                        ),
                        parameters=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "query": types.Schema(
                                    type=types.Type.STRING,
                                    description="User's problem description"
                                )
                            },
                            required=["query"]
                        )
                    )
                ]
            )
        ]
        
        logger.info("knowledge_agent_initialized", model=model_name)
    
    def _load_prompt(self) -> str:
        """Load system prompt from file"""
        prompt_path = "prompts/knowledge_agent.prompt"
        
        try:
            with open(prompt_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback inline prompt
            return """You are a Level 1 IT Support Specialist.

Your ONLY job is to search the knowledge base and provide solutions to technical problems.

WORKFLOW:
1. Use search_knowledge_base tool with the user's problem description
2. If solution found: Format it clearly with numbered steps
3. If NOT found: Return exactly "KB_NOT_FOUND" (no other text)

RULES:
- Always use the search_knowledge_base tool first
- Present solutions in clear, numbered steps
- Be professional but friendly
- If no solution exists, return only "KB_NOT_FOUND"
- Do NOT make up solutions - only use KB content

FORMAT:
When solution found:
"I found a solution for [problem]:

[Title from KB]

Steps:
1. [step 1]
2. [step 2]
...

Let me know if this resolves your issue!"

When NOT found:
"KB_NOT_FOUND"
"""
    
    def resolve(self, problem_description: str, trace_id: str) -> Dict[str, Any]:
        """
        Attempt to resolve a technical problem using the knowledge base.
        
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
            # Call LLM with tool access
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=problem_description)]
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    tools=self.tools,
                    temperature=0.3,  # Lower temp for more consistent KB lookups
                )
            )
            
            # Process response
            result = self._process_response(response, trace_id)
            
            logger.info(
                "knowledge_agent_completed",
                trace_id=trace_id,
                success=result["success"],
                article_id=result.get("article_id")
            )
            
            return result
            
        except Exception as e:
            logger.error("knowledge_agent_error", trace_id=trace_id, error=str(e))
            return {
                "success": False,
                "response": "I encountered an error searching the knowledge base.",
                "article_id": None
            }
    
    def _process_response(self, response: types.GenerateContentResponse, trace_id: str) -> Dict[str, Any]:
        """
        Process LLM response and execute tools if needed.
        
        Args:
            response: LLM response
            trace_id: Trace ID for logging
            
        Returns:
            Dict with resolution result
        """
        if not response.candidates:
            return {
                "success": False,
                "response": "KB_NOT_FOUND",
                "article_id": None
            }
        
        candidate = response.candidates[0]
        
        text_parts = []
        kb_result = None
        
        for part in candidate.content.parts:
            if part.text:
                text_parts.append(part.text)
            
            elif part.function_call:
                # Execute search_knowledge_base tool
                tool_name = part.function_call.name
                tool_args = dict(part.function_call.args)
                
                logger.info(
                    "knowledge_agent_tool_call",
                    trace_id=trace_id,
                    tool=tool_name,
                    query=tool_args.get("query", "")[:100]
                )
                
                kb_result = execute_tool(tool_name, tool_args)
        
        # Combine text response
        full_text = "\n".join(text_parts)
        
        # Check if solution was found
        if kb_result and kb_result.get("found"):
            return {
                "success": True,
                "response": full_text if full_text else f"Solution found: {kb_result['solution']}",
                "article_id": kb_result.get("article_id")
            }
        else:
            # Check if agent explicitly said not found
            if "KB_NOT_FOUND" in full_text or not kb_result or not kb_result.get("found"):
                return {
                    "success": False,
                    "response": "KB_NOT_FOUND",
                    "article_id": None
                }
            
            return {
                "success": True,
                "response": full_text,
                "article_id": None
            }