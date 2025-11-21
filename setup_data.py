import json
import sqlite3
import os

# --- CONFIGURAÇÃO ---
# Garante que a pasta data existe
os.makedirs("data", exist_ok=True)

KB_FILE = "data/knowledge_base.json"
TICKETS_DB_FILE = "data/tickets.db"
SESSIONS_DB_FILE = "data/sessions.db" # O ficheiro que te estava a falhar

# --- 1. GERAR BASE DE CONHECIMENTO (JSON) ---
def create_knowledge_base():
    kb_data = [
        {
            "id": 101,
            "category": "Hardware",
            "issue": "Printer not responding or printing",
            "keywords": ["printer", "print", "paper", "jam", "offline"],
            "solution": "1. Check if the printer is turned on and connected to the network.\n2. Restart the printer.\n3. Clear the print queue on your computer.\n4. Check for paper jams."
        },
        {
            "id": 102,
            "category": "Access",
            "issue": "VPN Connection Failed",
            "keywords": ["vpn", "connection", "network", "remote", "access"],
            "solution": "1. Ensure you have an active internet connection.\n2. Verify your MFA token is correct.\n3. Try switching the VPN protocol in settings to TCP.\n4. Reinstall the VPN client if the issue persists."
        },
        {
            "id": 103,
            "category": "Software",
            "issue": "Application crashing on startup",
            "keywords": ["crash", "app", "software", "freeze", "close"],
            "solution": "1. Check for software updates.\n2. Clear the application cache/temporary files.\n3. Restart your computer.\n4. If critical, request a reinstall via ticket."
        },
        {
            "id": 104,
            "category": "Security",
            "issue": "Password Reset Instructions",
            "keywords": ["password", "reset", "login", "forgot", "account"],
            "solution": "1. Go to the self-service portal at portal.company.com.\n2. Click 'Forgot Password'.\n3. Enter your employee ID.\n4. Follow the SMS verification steps."
        },
         {
            "id": 105,
            "category": "Email",
            "issue": "Outlook not syncing",
            "keywords": ["email", "outlook", "sync", "receiving", "sending"],
            "solution": "1. Check internet connection.\n2. Look for the 'Working Offline' toggle in the Send/Receive tab and turn it off.\n3. Close and reopen Outlook."
        }
    ]

    with open(KB_FILE, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, indent=4)
    
    print(f"[OK] Knowledge Base created/reset: {KB_FILE}")

# --- 2. GERAR BASE DE DADOS DE TICKETS (SQLite) ---
def create_ticket_db():
    # Apaga o ficheiro antigo se existir
    if os.path.exists(TICKETS_DB_FILE):
        os.remove(TICKETS_DB_FILE)
        print(f"[OK] Deleted old Tickets DB: {TICKETS_DB_FILE}")

    conn = sqlite3.connect(TICKETS_DB_FILE)
    cursor = conn.cursor()

    # Criar Tabela
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        issue_summary TEXT NOT NULL,
        priority TEXT CHECK(priority IN ('Low', 'Normal', 'High')) DEFAULT 'Normal',
        status TEXT CHECK(status IN ('Open', 'In Progress', 'Closed')) DEFAULT 'Open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(create_table_sql)

    # Dados de exemplo (Seed Data)
    sample_tickets = [
        ("user_123", "Laptop screen flickering", "Normal", "Open"),
        ("user_123", "Need access to Marketing folder", "Low", "Closed"),
        ("user_456", "Wifi not working on 2nd floor", "High", "In Progress")
    ]

    cursor.executemany("""
        INSERT INTO tickets (user_id, issue_summary, priority, status)
        VALUES (?, ?, ?, ?)
    """, sample_tickets)

    conn.commit()
    conn.close()
    print(f"[OK] Ticket Database created: {TICKETS_DB_FILE}")

# --- 3. LIMPAR BASE DE DADOS DE SESSÕES (Memória) ---
def reset_session_db():
    if os.path.exists(SESSIONS_DB_FILE):
        try:
            os.remove(SESSIONS_DB_FILE)
            print(f"[OK] Deleted Session Memory: {SESSIONS_DB_FILE}")
        except OSError as e:
            print(f"[WARN] Could not delete sessions DB (maybe in use?): {e}")
    else:
        print("[INFO] No session DB found to delete.")

if __name__ == "__main__":
    print("--- ✈️  Initializing SupportPilot Data Layer ---")
    
    create_knowledge_base()
    create_ticket_db()
    reset_session_db()
    
    print("--- ✅ Setup Complete ---")