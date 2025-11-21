"""
SupportPilot - Main Application Entry Point

This is the main CLI interface for the SupportPilot AI Agent system.
It provides an interactive terminal interface for users to interact with
the multi-agent IT support system.

Features:
- Persistent conversation memory (DatabaseSessionService)
- Multi-agent orchestration (Orchestrator → Knowledge/Ticket agents)
- Session-based user identity (enterprise-ready authentication model)
- Full observability logging (user inputs, tool calls, agent responses)

Architecture Flow:
    1. User authentication (login with User ID)
    2. Session initialization (create or resume)
    3. Conversation loop (user input → agent processing → response)
    4. Logging (all events captured to logs/support_pilot.log)

Usage:
    python main.py
    
    Enter User ID when prompted (e.g., "alice_123")
    Type 'quit' or 'exit' to terminate the session.

Requirements:
    - GOOGLE_API_KEY must be set in .env file
    - data/sessions.db will be created automatically
    - logs/ directory will be created for log files

Author: SupportPilot Team
"""

import asyncio
import uuid
import os
import warnings
import logging
from dotenv import load_dotenv

# --- LOG SUPPRESSION CONFIGURATION ---
# Suppress unnecessary warnings and verbose logs from dependencies
# This must be done BEFORE importing Google libraries
warnings.filterwarnings("ignore")
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'

# Suppress specific warning categories
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*non-text parts in the response.*")
warnings.filterwarnings("ignore", message=".*Default value is not supported.*")

# Silence specific loggers
logging.getLogger('google.adk').setLevel(logging.ERROR)
logging.getLogger('google.genai').setLevel(logging.ERROR)

logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)

logging.getLogger('google.generativeai').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

# --- CORE IMPORTS ---
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from src.agents.orchestrator import get_orchestrator_agent
from src.utils.logger import setup_logger

# --- APPLICATION CONFIGURATION ---
load_dotenv()  # Load environment variables from .env file
logger = setup_logger("SupportPilot_App")

# Application name (must match across all ADK components)
APP_NAME = "agents"

# Database URL for session persistence (SQLite)
SESSION_DB_URL = f"sqlite:///{os.path.abspath('data/sessions.db')}"


def print_banner():
    """
    Displays the SupportPilot welcome banner in the terminal.
    
    This provides a professional first impression and confirms the system
    is running with persistent memory enabled.
    """
    print("""
======================================================
✈️  S U P P O R T P I L O T   A G E N T  ✈️
======================================================
           Persistent Memory Enabled 🧠
======================================================
Commands:
  - Type 'quit', 'exit', or 'bye' to terminate
  - Ask technical questions for KB search
  - Request ticket operations (create/status/update)
======================================================
""")


async def check_user_history(session_service: DatabaseSessionService, user_id: str) -> bool:
    """
    Checks if a user has existing session history in the database.
    
    This allows the system to provide personalized greetings:
    - New users: "Hello! Creating your profile..."
    - Returning users: "Welcome back!"
    
    Args:
        session_service (DatabaseSessionService): The session management service.
        user_id (str): The user's unique identifier.
    
    Returns:
        bool: True if the user has previous sessions, False otherwise.
    
    Note:
        This function suppresses exceptions to handle database initialization
        scenarios gracefully (e.g., first-time setup).
    """
    try:
        response = await session_service.list_sessions(app_name=APP_NAME, user_id=user_id)
        if response.sessions:
            return True
    except Exception:
        # Silently handle errors (e.g., database not yet initialized)
        pass
    return False


async def main_loop():
    """
    Main application loop that handles user authentication and conversation.
    
    Flow:
        1. Display banner
        2. Initialize infrastructure (session service, orchestrator, runner)
        3. User login (enter User ID)
        4. Check user history (new vs returning)
        5. Create fresh session with initial state
        6. Enter conversation loop:
           - Accept user input
           - Process with agent
           - Display response
           - Log all events
        7. Exit on quit command
    
    Session Management:
        - Each run creates a NEW session (fresh conversation)
        - Session state includes: user:user_id, user:name
        - Conversation history is persisted to database
    
    Logging:
        All interactions are logged to logs/support_pilot.log:
        - USER_INPUT: User messages
        - TOOL_CALL: Agent tool invocations
        - TOOL_OUTPUT: Tool results
        - AGENT_RESPONSE: Agent replies
        - CRITICAL_ERROR: System failures
    
    Error Handling:
        - KeyboardInterrupt (Ctrl+C): Graceful shutdown
        - General exceptions: Logged and conversation terminates
    """
    print_banner()
    
    # === STEP 1: INITIALIZE INFRASTRUCTURE ===
    session_service = DatabaseSessionService(db_url=SESSION_DB_URL)
    orchestrator = get_orchestrator_agent()
    runner = Runner(
        agent=orchestrator,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # === STEP 2: USER AUTHENTICATION ===
    # In production, this would come from SSO/Active Directory
    current_user_id = input("🔐 Enter User ID (e.g., jose_kaggle): ").strip() or "guest"
    
    # === STEP 3: CHECK USER HISTORY ===
    user_exists = await check_user_history(session_service, current_user_id)
    
    if user_exists:
        greeting = f"👋 Welcome back, {current_user_id}! (New Session Started)"
    else:
        greeting = f"👋 Hello {current_user_id}! Creating your profile..."
    
    # === STEP 4: CREATE NEW SESSION ===
    # Each run starts with a clean session (fresh conversation context)
    current_session_id = str(uuid.uuid4())
    
    # Initial session state (persistent across conversation)
    initial_state = {
        "user:user_id": current_user_id,  # Authenticated user identifier
        "user:name": current_user_id       # Display name (same as ID for simplicity)
    }
    
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=current_user_id,
        session_id=current_session_id,
        state=initial_state
    )
    
    print("-" * 60)
    print(f"🤖 SupportPilot: {greeting}")
    
    # === STEP 5: CONVERSATION LOOP ===
    while True:
        try:
            # Get user input
            user_input = input(f"\n👤 {current_user_id} > ").strip()
            
            # Skip empty inputs
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\n👋 Saving memory... Goodbye!")
                logger.info(f"User {current_user_id} logged out.")
                break  # Exit the loop and terminate the program
            
            # Log user input
            logger.info(f"USER_INPUT [User:{current_user_id}]: {user_input}")
            
            # Create ADK content object
            content = types.Content(
                role="user",
                parts=[types.Part(text=user_input)]
            )
            
            # Visual feedback (processing indicator)
            print("🤖 SupportPilot ", end="", flush=True)
            full_text = ""  # Accumulate agent response text
            
            # === STEP 6: EXECUTE AGENT ===
            async for event in runner.run_async(
                user_id=current_user_id,
                session_id=current_session_id,
                new_message=content
            ):
                if event.content and event.content.parts:
                    part = event.content.parts[0]
                    
                    # Event Type 1: Tool Call (Agent requesting tool execution)
                    if part.function_call:
                        # Visual feedback: processing dots
                        print(".", end="", flush=True)
                        
                        # Log tool invocation
                        logger.info(
                            f"TOOL_CALL: {part.function_call.name} | "
                            f"Args: {part.function_call.args}"
                        )
                    
                    # Event Type 2: Tool Response (Tool returning data to agent)
                    elif part.function_response:
                        # Log tool output (captured for observability)
                        logger.info(
                            f"TOOL_OUTPUT: {part.function_response.name} | "
                            f"Response: {str(part.function_response.response)[:100]}..."
                        )
                    
                    # Event Type 3: Text Response (Agent speaking to user)
                    elif part.text:
                        text_clean = part.text.strip()
                        
                        # Ignore empty or placeholder responses
                        if text_clean and text_clean != "None":
                            print(f"\n{text_clean}")
                            full_text += text_clean
                            
                            # Log agent response
                            logger.info(f"AGENT_RESPONSE: {text_clean}")
            
            # Handle silent completions (action completed without text output)
            if not full_text:
                print("\n(Action completed silently)")
        
        except KeyboardInterrupt:
            # User pressed Ctrl+C
            print("\n⚠️  Interrupted by user.")
            logger.info(f"User {current_user_id} interrupted session.")
            break
        
        except Exception as e:
            # Unexpected error occurred
            print(f"\n❌ Error: {e}")
            logger.error(f"CRITICAL_ERROR: {e}")
            break


if __name__ == "__main__":
    # Boot sequence: Verify logger is working
    test_logger = setup_logger("BOOT_TEST")
    test_logger.info("=== SupportPilot System Starting ===")
    
    # Run the main application loop
    asyncio.run(main_loop())
    
    # Shutdown sequence
    test_logger.info("=== SupportPilot System Shutdown ===")