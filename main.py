import asyncio
import uuid
import os
import warnings
import logging
import sys
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DE LOGS ---
warnings.filterwarnings("ignore")
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'

logging.getLogger('google.adk').setLevel(logging.ERROR)
logging.getLogger('google.genai').setLevel(logging.ERROR)
logging.getLogger('absl').setLevel(logging.ERROR)

# Imports
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from src.agents.orchestrator import get_orchestrator_agent
from src.utils.logger import setup_logger

# Configurações
load_dotenv()
logger = setup_logger("SupportPilot_App")

APP_NAME = "agents"
SESSION_DB_URL = f"sqlite:///{os.path.abspath('data/sessions.db')}"

def print_banner():
    print("""
    ======================================================
       ✈️   S U P P O R T   P I L O T   A G E N T   ✈️
    ======================================================
    Status: Online | Memory: Persistent (SQLite)
    
    AVAILABLE COMMANDS:
    • Ask technical questions (e.g., "VPN is down")
    • Manage tickets (e.g., "Create ticket", "Status of tickets")
    • Check identity (e.g., "Who am I?")
    • System: Type 'quit', 'exit' or 'bye' to close.
    ======================================================
    """)

async def check_user_history(session_service, user_id):
    """Verifica se o utilizador já tem histórico na BD."""
    try:
        resp = await session_service.list_sessions(app_name=APP_NAME, user_id=user_id)
        if resp.sessions:
            return True
    except:
        pass
    return False

async def main_loop():
    print_banner()
    
    # 1. Inicializar Infraestrutura
    session_service = DatabaseSessionService(db_url=SESSION_DB_URL)
    orchestrator = get_orchestrator_agent()
    runner = Runner(agent=orchestrator, app_name=APP_NAME, session_service=session_service)

    # 2. Login Único (Simplificação Realista)
    current_user_id = input("🔐 Enter User ID (e.g., jose_kaggle): ").strip() or "guest"
    
    # 3. Configuração da Sessão (Verificação de Histórico)
    user_exists = await check_user_history(session_service, current_user_id)
    
    if user_exists:
        greeting = f"👋 Welcome back, {current_user_id}! (New Session Started)"
    else:
        greeting = f"👋 Hello {current_user_id}! Creating your profile..."

    # Criar Sessão Fresca
    current_session_id = str(uuid.uuid4())
    
    # Estado Inicial (Persistente)
    initial_state = {
        "user:user_id": current_user_id,
        "user:name": current_user_id
    }
    
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=current_user_id,
        session_id=current_session_id,
        state=initial_state
    )
    
    print("-" * 60)
    print(f"🤖 SupportPilot: {greeting}")

    # 4. Loop de Conversação (Único)
    while True:
        try:
            user_input = input(f"\n👤 {current_user_id} > ").strip()
            
            if not user_input: continue
            if user_input.lower() in ["quit", "exit", "bye"]:
                print("\n👋 Saving memory... Goodbye!")
                break # Sai do loop e termina o programa

            # Log
            logger.info(f"USER_INPUT: {user_input}")

            content = types.Content(role="user", parts=[types.Part(text=user_input)])
            print("🤖 SupportPilot ", end="", flush=True)
            
            full_text = ""
            
            # Execução
            async for event in runner.run_async(
                user_id=current_user_id, session_id=current_session_id, new_message=content
            ):
                if event.content and event.content.parts:
                    part = event.content.parts[0]
                    
                    # Tool Call
                    if part.function_call:
                        print(".", end="", flush=True)
                        logger.info(f"TOOL_CALL: {part.function_call.name}")
                    
                    # Tool Response (Captura silenciosa para log)
                    elif part.function_response:
                        logger.info(f"TOOL_OUTPUT: {part.function_response.name}")
                    
                    # Agente Response
                    elif part.text:
                        text_clean = part.text.strip()
                        if text_clean and text_clean != "None":
                            print(f"\n{text_clean}")
                            full_text += text_clean
                            logger.info(f"AGENT_RESPONSE: {text_clean}")

            if not full_text:
                print("\n(Action completed silently)")

        except KeyboardInterrupt:
            print("\n⚠️ Interrupted.")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.error(f"CRITICAL_ERROR: {e}")
            break

if __name__ == "__main__":
    asyncio.run(main_loop())