import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
# Importa o nosso logger
from src.utils.logger import setup_logger

# Inicializa o logger globalmente para este módulo
logger = setup_logger("TestRunner")

async def run_session(
    runner_instance: Runner,
    session_service: InMemorySessionService,
    user_id: str,
    user_queries: list[str] | str = None,
    session_name: str = "default",
):
    """
    Helper function to run a chat session with OBSERVABILITY.
    """
    print(f"\n--- Session: {session_name} ---")
    logger.info(f"Starting Session: {session_name} | User: {user_id}")

    app_name = runner_instance.app_name

    try:
        session = await session_service.create_session(
            app_name=app_name, user_id=user_id, session_id=session_name
        )
        logger.info(f"Created new session: {session.id}")
    except Exception:
        session = await session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_name
        )
        logger.info(f"Resumed session: {session.id}")

    if user_queries:
        if isinstance(user_queries, str):
            user_queries = [user_queries]

        for query_text in user_queries:
            print(f"\nUser > {query_text}")
            # Log User Input
            logger.info(f"USER_INPUT [User:{user_id}]: {query_text}")

            query_content = types.Content(role="user", parts=[types.Part(text=query_text)])

            async for event in runner_instance.run_async(
                user_id=user_id, session_id=session.id, new_message=query_content
            ):
                if event.content and event.content.parts:
                    # Log Raw Events (Tracing)
                    # logger.debug(f"RAW_EVENT: {event}") 
                    
                    part = event.content.parts[0]
                    
                    # Check for Function Calls (Tool Usage)
                    if part.function_call:
                        tool_name = part.function_call.name
                        logger.info(f"TOOL_CALL: {tool_name} | Args: {part.function_call.args}")
                        print(f"[System] Calling Tool: {tool_name}...")

                    # Check for Function Response
                    elif part.function_response:
                        tool_name = part.function_response.name
                        # Truncate output for logs if too long
                        output_sample = str(part.function_response.response)[:100] 
                        logger.info(f"TOOL_OUTPUT: {tool_name} | Result: {output_sample}...")

                    # Check for Text Response (Agent Reply)
                    elif part.text and part.text != "None":
                        print(f"Agent > {part.text}")
                        logger.info(f"AGENT_RESPONSE: {part.text}")
    else:
        print("No queries provided.")