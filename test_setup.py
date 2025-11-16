"""
Quick Setup Test for SupportPilot

Run this to verify all components are working before full testing.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from src.agents import OrchestratorAgent, KnowledgeAgent, CreationAgent, QueryAgent
        print("   ✓ Agents imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import agents: {e}")
        return False
    
    try:
        from src.tools import search_knowledge_base, create_support_ticket, get_ticket_status
        print("   ✓ Tools imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import tools: {e}")
        return False
    
    try:
        from src.core import get_database, get_knowledge_base, TraceModel, metrics_collector
        print("   ✓ Core modules imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import core: {e}")
        return False
    
    try:
        from src.models import SessionMetadata, IntentType, AgentType
        print("   ✓ Models imported successfully")
    except Exception as e:
        print(f"   ✗ Failed to import models: {e}")
        return False
    
    return True


def test_env():
    """Test that environment is configured"""
    print("\n🔍 Testing environment...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        print(f"   ✓ API key found: {api_key[:10]}...")
        return True
    else:
        print("   ✗ GOOGLE_API_KEY not found in environment")
        print("   → Create .env file with: GOOGLE_API_KEY=your-key-here")
        return False


def test_database():
    """Test database initialization"""
    print("\n🔍 Testing database...")
    
    try:
        from src.core import get_database, get_knowledge_base
        
        db = get_database()
        print("   ✓ Database initialized")
        
        kb = get_knowledge_base()
        print(f"   ✓ Knowledge base loaded: {len(kb.articles)} articles")
        
        return True
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")
        return False


def test_tools():
    """Test tools directly"""
    print("\n🔍 Testing tools...")
    
    try:
        from src.tools import search_knowledge_base, create_support_ticket, get_ticket_status
        
        # Test KB search
        result = search_knowledge_base("VPN")
        if result["found"]:
            print(f"   ✓ KB search working (found: {result['title']})")
        else:
            print("   ⚠ KB search returned no results (expected for test)")
        
        # Test ticket creation
        ticket_result = create_support_ticket(
            user_id="test_user",
            description="Test ticket",
            priority="Normal"
        )
        if ticket_result["success"]:
            print(f"   ✓ Ticket creation working (ID: {ticket_result['ticket_id']})")
        else:
            print(f"   ✗ Ticket creation failed")
            return False
        
        # Test ticket query
        query_result = get_ticket_status("test_user")
        if query_result["found"]:
            print(f"   ✓ Ticket query working (found {query_result['count']} ticket(s))")
        else:
            print("   ⚠ No tickets found (might be expected)")
        
        return True
    except Exception as e:
        print(f"   ✗ Tools test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """Test that agents can be initialized"""
    print("\n🔍 Testing agent initialization...")
    
    try:
        from src.agents import KnowledgeAgent, CreationAgent, QueryAgent, OrchestratorAgent
        
        # Note: This will fail if GOOGLE_API_KEY is not set
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("   ⚠ Skipping agent test (no API key)")
            return True
        
        print("   → Initializing KnowledgeAgent...")
        ka = KnowledgeAgent(api_key=api_key)
        print("   ✓ KnowledgeAgent initialized")
        
        print("   → Initializing CreationAgent...")
        ca = CreationAgent(api_key=api_key)
        print("   ✓ CreationAgent initialized")
        
        print("   → Initializing QueryAgent...")
        qa = QueryAgent(api_key=api_key)
        print("   ✓ QueryAgent initialized")
        
        print("   → Initializing OrchestratorAgent...")
        oa = OrchestratorAgent(api_key=api_key)
        print("   ✓ OrchestratorAgent initialized")
        
        return True
    except Exception as e:
        print(f"   ✗ Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("╔════════════════════════════════════════════════════════╗")
    print("║         SupportPilot Setup Verification               ║")
    print("╚════════════════════════════════════════════════════════╝\n")
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_env()))
    results.append(("Database", test_database()))
    results.append(("Tools", test_tools()))
    results.append(("Agent Initialization", test_agent_initialization()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:.<40} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed! System is ready.")
        print("\nNext steps:")
        print("  python src/main.py              # Interactive mode")
        print("  python src/main.py --demo       # Demo scenarios")
    else:
        print("❌ Some tests failed. Please fix issues above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())