"""
SupportPilot - Main Entry Point

This is the CLI interface for interacting with the SupportPilot multi-agent system.
For the Kaggle capstone demo, this provides a simple way to test all features.

Usage:
    python src/main.py              # Interactive mode
    python src/main.py --demo       # Run demo scenarios
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.agents.orchestrator import OrchestratorAgent
from src.core.observability import metrics_collector, logger
from src.core.database import get_database, get_knowledge_base


def print_banner():
    """Print welcome banner"""
    print("""
╔════════════════════════════════════════════════════════╗
║                    SupportPilot                        ║
║            AI-Powered IT Support Assistant             ║
║                                                        ║
║  Multi-Agent System | ADK-Powered | Level 1 Support   ║
╚════════════════════════════════════════════════════════╝
""")


def print_help():
    """Print available commands"""
    print("""
Available commands:
  /help      - Show this help message
  /status    - Show system metrics
  /clear     - Clear screen
  /reset     - Reset session (clear conversation history)
  /quit      - Exit the application
  
Just type your IT support question to get started!

Examples:
  • "My VPN is not connecting"
  • "I forgot my password"
  • "Create a ticket for printer issues"
  • "What are my tickets?"
""")


def initialize_system():
    """
    Initialize the SupportPilot system.
    
    Returns:
        OrchestratorAgent: Initialized orchestrator
    """
    print("🔧 Initializing SupportPilot...\n")
    
    # Load environment variables
    load_dotenv()
    
    # Verify API key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment")
        print("\nPlease set your API key:")
        print("  export GOOGLE_API_KEY='your-api-key-here'")
        print("\nOr create a .env file with:")
        print("  GOOGLE_API_KEY=your-api-key-here")
        sys.exit(1)
    
    # Initialize database
    print("📦 Initializing database...")
    db = get_database()
    print("   ✓ Database ready")
    
    # Load knowledge base
    print("📚 Loading knowledge base...")
    kb = get_knowledge_base()
    print(f"   ✓ Loaded {len(kb.articles)} articles")
    
    # Initialize orchestrator (which initializes all agents)
    print("🤖 Initializing multi-agent system...")
    print("   - Orchestrator Agent")
    print("   - Knowledge Agent (L1 Support)")
    print("   - Creation Agent (L2 Escalation)")
    print("   - Query Agent (Status Checking)")
    
    orchestrator = OrchestratorAgent(api_key=api_key)
    print("   ✓ All agents ready")
    
    print("\n✅ System initialized successfully!\n")
    
    return orchestrator


def run_interactive_session(orchestrator: OrchestratorAgent):
    """
    Run interactive CLI session.
    
    Args:
        orchestrator: Initialized OrchestratorAgent
    """
    print_help()
    
    # For demo purposes, use a fixed user_id
    # In production, this would come from authentication
    user_id = "demo_user_001"
    
    print(f"\n💬 Chatting as: {user_id}")
    print(f"📝 Session: interactive")
    print("=" * 60)
    
    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                if handle_command(user_input, orchestrator, user_id):
                    break  # Exit if /quit was called
                continue
            
            # Process message through orchestrator
            print("\n🤖 SupportPilot: ", end="", flush=True)
            
            try:
                response = orchestrator.process_message(user_id, user_input)
                print(response)
            except Exception as e:
                print(f"\n❌ Error processing message: {str(e)}")
                logger.error("main_processing_error", error=str(e), user_id=user_id)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            logger.error("main_loop_error", error=str(e))
            print(f"\n❌ Unexpected error: {str(e)}")


def handle_command(command: str, orchestrator: OrchestratorAgent, user_id: str) -> bool:
    """
    Handle special commands.
    
    Args:
        command: Command string starting with /
        orchestrator: Orchestrator instance
        user_id: Current user ID
        
    Returns:
        bool: True if should exit, False otherwise
    """
    command = command.lower()
    
    if command == "/help":
        print_help()
    
    elif command == "/status":
        print("\n" + metrics_collector.get_report())
    
    elif command == "/clear":
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
    
    elif command == "/reset":
        # Reset session by clearing metadata
        if hasattr(orchestrator, '_test_metadata_store'):
            if user_id in orchestrator._test_metadata_store:
                del orchestrator._test_metadata_store[user_id]
        print("\n✓ Session reset. Starting fresh conversation.")
    
    elif command == "/quit":
        print("\n👋 Goodbye!")
        return True
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Type /help for available commands")
    
    return False


def run_demo_scenarios(orchestrator: OrchestratorAgent):
    """
    Run predefined demo scenarios for video recording.
    
    This demonstrates all key features of SupportPilot:
    1. L1 Resolution (happy path)
    2. KB Not Found (auto-escalation)
    3. User Dissatisfaction (negative signal detection)
    4. Explicit Ticket Request
    5. Status Query
    
    Args:
        orchestrator: Initialized OrchestratorAgent
    """
    user_id = "demo_user_video"
    
    scenarios = [
        {
            "name": "Scenario 1: Happy Path (L1 Resolution)",
            "description": "User reports common issue that KB can resolve",
            "messages": [
                "My VPN is not connecting to the corporate network"
            ],
            "expected": "KB solution provided, issue resolved at L1"
        },
        {
            "name": "Scenario 2: KB Not Found → Auto Escalation",
            "description": "User reports issue not in KB, automatic ticket creation",
            "messages": [
                "I need help integrating quantum computing with our blockchain infrastructure"
            ],
            "expected": "No KB match, automatic escalation to L2, ticket created"
        },
        {
            "name": "Scenario 3: User Dissatisfaction → Escalation",
            "description": "KB solution attempted but user reports it didn't work",
            "messages": [
                "My printer is not working",
                "I tried all those steps and it still doesn't work"
            ],
            "expected": "KB solution provided, negative signal detected, escalated to L2"
        },
        {
            "name": "Scenario 4: Explicit Ticket Request",
            "description": "User directly asks to create a ticket",
            "messages": [
                "I need to create a ticket for laptop battery replacement"
            ],
            "expected": "Direct ticket creation bypassing KB search"
        },
        {
            "name": "Scenario 5: Check Ticket Status",
            "description": "User queries their existing tickets",
            "messages": [
                "What are my open tickets?"
            ],
            "expected": "List of user's tickets with status information"
        }
    ]
    
    print("\n" + "="*60)
    print("🎬 RUNNING DEMO SCENARIOS FOR KAGGLE CAPSTONE")
    print("="*60)
    print("\nThis demo showcases:")
    print("  ✓ Multi-agent system (Orchestrator + 3 specialized agents)")
    print("  ✓ Custom tools (search_kb, create_ticket, get_ticket_status)")
    print("  ✓ Session management & state tracking")
    print("  ✓ Negative signal detection")
    print("  ✓ Observability (tracing & metrics)")
    print("\n" + "="*60)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n\n{'='*60}")
        print(f"📝 {scenario['name']}")
        print(f"📖 {scenario['description']}")
        print(f"🎯 Expected: {scenario['expected']}")
        print('='*60)
        
        for j, msg in enumerate(scenario['messages'], 1):
            print(f"\n👤 User (Message {j}): {msg}")
            print(f"🤖 SupportPilot: ", end="", flush=True)
            
            try:
                response = orchestrator.process_message(user_id, msg)
                print(response)
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                logger.error("demo_error", scenario=scenario['name'], error=str(e))
            
            if j < len(scenario['messages']):
                input("\n⏸️  Press Enter to continue to next message...")
        
        if i < len(scenarios):
            input("\n⏸️  Press Enter to continue to next scenario...")
    
    print("\n\n" + "="*60)
    print("✅ DEMO COMPLETE")
    print("="*60)
    print("\nFinal Metrics:")
    print(metrics_collector.get_report())
    
    print("\n📊 Agent Flow Summary:")
    print("  • Scenario 1: Orchestrator → Knowledge Agent → L1 Resolution")
    print("  • Scenario 2: Orchestrator → Knowledge Agent → Creation Agent → L2 Escalation")
    print("  • Scenario 3: Orchestrator → Knowledge → (negative signal) → Creation → L2")
    print("  • Scenario 4: Orchestrator → Creation Agent → L2 Escalation")
    print("  • Scenario 5: Orchestrator → Query Agent → Status Retrieved")


def main():
    """Main entry point"""
    print_banner()
    
    # Initialize system
    try:
        orchestrator = initialize_system()
    except Exception as e:
        print(f"\n❌ Failed to initialize system: {str(e)}")
        logger.error("initialization_failed", error=str(e))
        sys.exit(1)
    
    # Check if demo mode
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo_scenarios(orchestrator)
    else:
        run_interactive_session(orchestrator)


if __name__ == "__main__":
    main()