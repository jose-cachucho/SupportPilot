"""
SupportPilot - Main Application Entry Point

This is the main CLI interface for the SupportPilot AI Agent system.
It provides an interactive terminal interface for users to interact with
the multi-agent IT support system with role-based access control (RBAC).

Features:
- Persistent conversation memory (DatabaseSessionService)
- Multi-agent orchestration (Orchestrator → Knowledge/Ticket agents)
- Session-based user identity (enterprise-ready authentication model)
- Role-Based Access Control (end_user vs service_desk_agent)
- Full observability logging (user inputs, tool calls, agent responses)

Architecture Flow:
    1. CLI argument parsing (user_id, role)
    2. Role validation and defaults
    3. Session initialization (create or resume)
    4. Conversation loop (user input → agent processing → response)
    5. Logging (all events captured to logs/support_pilot.log)

Usage:
    # As end user (default role)
    python main.py --user_id alice_123
    
    # As service desk agent
    python main.py --user_id john_support --role service_desk_agent
    
    # Guest mode (interactive login)
    python main.py
    
    # Type 'quit' or 'exit' to terminate the session

Roles:
    - end_user: Regular users (create tickets, view own tickets)
    - service_desk_agent: Support staff (view all tickets, update status)

Requirements:
    - GOOGLE_API_KEY must be set in .env file
    - data/sessions.db will be created automatically
    - logs/ directory will be created for log files

Author: SupportPilot Team
"""

import asyncio
import argparse
import uuid
import os
import warnings
import logging
from dotenv import load_dotenv

# --- LOG SUPPRESSION CONFIGURATION ---
# Suppress unnecessary warnings and verbose logs from dependencies
# This must be done BEFORE importing Google libraries
warnings.filterwarnings("ignore")

# Suppress specific warning categories
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("google_genai").setLevel(logging.ERROR)
logging.getLogger("google_genai.types").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*non-text parts in the response.*")
warnings.filterwarnings("ignore", message=".*Default value is not supported.*")

os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'

# Silence specific loggers
logging.getLogger('google.adk').setLevel(logging.ERROR)
logging.getLogger('google.genai').setLevel(logging.ERROR)
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
    is running with persistent memory and role-based access control enabled.
    """
    print("""
======================================================
✈️  S U P P O R T P I L O T   A G E N T  ✈️
======================================================
     Persistent Memory + RBAC Enabled 🧠🔐
======================================================
Commands:
  - Type 'quit', 'exit', or 'bye' to terminate
  - Ask technical questions for KB search
  - Request ticket operations (create/status/update)

Roles:
  - end_user: Create tickets, view own tickets
  - service_desk_agent: View all tickets, update status
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
    Main application loop that handles CLI arguments, authentication, and conversation.
    
    Flow:
        0. Parse CLI arguments (--user_id, --role)
        1. Display banner
        2. Initialize infrastructure (session service, orchestrator, runner)
        3. Validate and set user role
        4. User authentication (from CLI or interactive input)
        5. Check user history (new vs returning)
        6. Create fresh session with initial state (including role)
        7. Enter conversation loop:
           - Accept user input
           - Process with agent
           - Display response
           - Log all events
        8. Exit on quit command
    
    CLI Arguments:
        --user_id: User identifier (default: "guest", triggers interactive input)
        --role: User role - "end_user" or "service_desk_agent" (default: "end_user")
    
    Session Management:
        - Each run creates a NEW session (fresh conversation)
        - Session state includes: user:user_id, user:name, user:role
        - Conversation history is persisted to database
    
    Role-Based Access Control:
        - end_user: Limited permissions (own tickets only)
        - service_desk_agent: Full permissions (all tickets, status updates)
    
    Logging:
        All interactions are logged to logs/support_pilot.log:
        - USER_INPUT: User messages
        - TOOL_CALL: Agent tool invocations
        - TOOL_OUTPUT: Tool results
        - AGENT_RESPONSE: Agent replies
        - CRITICAL_ERROR: System failures
        - USER_ROLE: Role information for audit trail
    
    Error Handling:
        - KeyboardInterrupt (Ctrl+C): Graceful shutdown
        - General exceptions: Logged and conversation terminates
    """
    
    # === STEP 0: CLI ARGUMENT PARSING ===
    parser = argparse.ArgumentParser(
        description="SupportPilot - AI-Powered IT Support Assistant with RBAC",
        epilog="Example: python main.py --user_id alice --role service_desk_agent"
    )
    parser.add_argument(
        "--user_id",
        type=str,
        default="guest",
        help="User identifier (default: guest, will prompt for input)"
    )
    parser.add_argument(
        "--role",
        type=str,
        default="end_user",
        help="User role: end_user or service_desk_agent (default: end_user)"
    )
    args = parser.parse_args()
    
    # Validate role against allowed values
    allowed_roles = ["end_user", "service_desk_agent"]
    user_role = args.role if args.role in allowed_roles else "end_user"
    
    # Warn if invalid role was provided
    if args.role not in allowed_roles:
        print(f"⚠️  Warning: Invalid role '{args.role}'. Defaulting to 'end_user'.")
        print(f"   Allowed roles: {', '.join(allowed_roles)}\n")
    
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
    # From CLI arguments, or interactive input if user_id is "guest"
    if args.user_id == "guest":
        current_user_id = input("🔐 Enter User ID (default: guest): ").strip() or "guest"
    else:
        current_user_id = args.user_id
    
    # === STEP 3: CHECK USER HISTORY ===
    user_exists = await check_user_history(session_service, current_user_id)
    
    # Format role for display
    role_display = user_role.replace('_', ' ').title()
    
    if user_exists:
        greeting = f"👋 Welcome back, {current_user_id}! (New Session Started)"
    else:
        greeting = f"👋 Hello {current_user_id}! Creating your profile..."
    
    # === STEP 4: CREATE NEW SESSION ===
    # Each run starts with a clean session (fresh conversation context)
    current_session_id = str(uuid.uuid4())
    
    # Initial session state (persistent across conversation)
    initial_state = {
        "user:user_id": current_user_id,    # Authenticated user identifier
        "user:name": current_user_id,        # Display name (same as ID for simplicity)
        "user:role": user_role               # User role for RBAC
    }
    
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=current_user_id,
        session_id=current_session_id,
        state=initial_state
    )
    
    print("-" * 60)
    print(f"🤖 SupportPilot: {greeting}")
    print(f"🔐 Role: {role_display}")
    logger.info(f"Session started | User: {current_user_id} | Role: {user_role}")
    
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
            has_printed_newline = False  # Track if we've printed a newline after dots
            
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
                        # Log tool output (for observability only - DO NOT PRINT)
                        response_data = part.function_response.response
                        
                        logger.info(
                            f"TOOL_OUTPUT: {part.function_response.name} | "
                            f"Response: {str(response_data)[:100]}..."
                        )
                    
                    # Event Type 3: Text Response (Agent's final/intermediate response)
                    elif part.text:
                        text_clean = part.text.strip()
                        
                        # Only process non-empty, meaningful text
                        if text_clean and text_clean.lower() != "none":
                            # Print newline after dots (only once)
                            if not has_printed_newline:
                                print()  # New line after the dots
                                has_printed_newline = True
                            
                            # Print the agent's response
                            print(text_clean)
                            full_text += text_clean
                            
                            # Log agent response
                            logger.info(f"AGENT_RESPONSE: {text_clean}")
            
            # Handle silent completions (action completed without text output)
            if not full_text:
                print("\n⚠️  (No response from agent - check logs for details)")
        
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