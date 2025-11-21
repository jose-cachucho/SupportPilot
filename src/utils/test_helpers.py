"""
Test Helper Utilities for SupportPilot

This module provides helper functions for running agent sessions with
full observability. It captures and logs all agent interactions including:
- User inputs
- Tool calls and responses
- Agent text outputs
- Raw events for debugging

Useful for:
- Integration testing
- Development/debugging
- Demonstrating agent behavior

Usage:
    from src.utils.test_helpers import run_session
    
    await run_session(
        runner_instance=runner,
        session_service=session_service,
        user_id="test_user",
        user_queries=["Help with printer"],
        session_name="test_session_1"
    )

Author: SupportPilot Team
"""

import logging
from typing import Union, List

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import custom logger
from src.utils.logger import setup_logger

# Initialize module-level logger
logger = setup_logger("TestRunner")


async def run_session(
    runner_instance: Runner,
    session_service: InMemorySessionService,
    user_id: str,
    user_queries: Union[List[str], str, None] = None,
    session_name: str = "default",
) -> None:
    """
    Executes a test session with full observability logging.
    
    This helper function orchestrates a complete conversation session,
    logging every interaction for analysis and debugging purposes.
    
    Args:
        runner_instance (Runner): The ADK Runner instance with the agent.
        session_service (InMemorySessionService): Session management service.
        user_id (str): Unique identifier for the user.
        user_queries (Union[List[str], str, None], optional): 
            Query or list of queries to process. If None, only creates session.
        session_name (str, optional): Session identifier. Defaults to "default".
    
    Returns:
        None
    
    Logging:
        - INFO: User inputs, agent responses, tool calls/outputs
        - DEBUG: Raw event data (if enabled)
    
    Example:
        >>> await run_session(
        ...     runner_instance=runner,
        ...     session_service=session_service,
        ...     user_id="alice_123",
        ...     user_queries=["My printer is offline", "Create a ticket"],
        ...     session_name="alice_session_1"
        ... )
    """
    print(f"\n{'=' * 60}")
    print(f"📋 Session: {session_name}")
    print(f"{'=' * 60}")
    logger.info(f"Starting Session: {session_name} | User: {user_id}")
    
    app_name = runner_instance.app_name
    
    # 1. Create or resume session
    try:
        session = await session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_name
        )
        logger.info(f"Created new session: {session.id}")
    except Exception:
        # Session already exists, resume it
        session = await session_service.get_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_name
        )
        logger.info(f"Resumed existing session: {session.id}")
    
    # 2. Process user queries if provided
    if user_queries:
        # Convert single string to list for uniform processing
        if isinstance(user_queries, str):
            user_queries = [user_queries]
        
        for query_text in user_queries:
            print(f"\n👤 User > {query_text}")
            logger.info(f"USER_INPUT [User:{user_id}]: {query_text}")
            
            # Create content object for ADK
            query_content = types.Content(
                role="user",
                parts=[types.Part(text=query_text)]
            )
            
            # 3. Execute agent and process events
            async for event in runner_instance.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=query_content
            ):
                if event.content and event.content.parts:
                    part = event.content.parts[0]
                    
                    # Event Type 1: Function Call (Tool Usage)
                    if part.function_call:
                        tool_name = part.function_call.name
                        tool_args = part.function_call.args
                        
                        logger.info(f"TOOL_CALL: {tool_name} | Args: {tool_args}")
                        print(f"🔧 [System] Calling Tool: {tool_name}...")
                    
                    # Event Type 2: Function Response (Tool Output)
                    elif part.function_response:
                        tool_name = part.function_response.name
                        # Truncate output for readability in logs
                        output_sample = str(part.function_response.response)[:100]
                        
                        logger.info(f"TOOL_OUTPUT: {tool_name} | Result: {output_sample}...")
                    
                    # Event Type 3: Text Response (Agent Reply)
                    elif part.text and part.text != "None":
                        print(f"🤖 Agent > {part.text}")
                        logger.info(f"AGENT_RESPONSE: {part.text}")
                    
                    # Uncomment for deep debugging (logs ALL raw events)
                    # logger.debug(f"RAW_EVENT: {event}")
    
    else:
        print("ℹ️  No queries provided. Session created but idle.")
        logger.info("Session created without queries.")