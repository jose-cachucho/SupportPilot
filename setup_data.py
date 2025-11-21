"""
SupportPilot Data Layer Initialization Script

This script initializes the foundational data structures for SupportPilot:
1. Knowledge Base (JSON) - Contains IT troubleshooting solutions
2. Tickets Database (SQLite) - Stores support ticket records
3. Sessions Database (SQLite) - Manages conversation memory (reset for clean state)

Usage:
    python setup_data.py

Author: SupportPilot Team
License: MIT
"""

import json
import sqlite3
import os

# --- CONFIGURATION ---
# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

KB_FILE = "data/knowledge_base.json"
TICKETS_DB_FILE = "data/tickets.db"
SESSIONS_DB_FILE = "data/sessions.db"


# --- 1. GENERATE KNOWLEDGE BASE (JSON) ---
def create_knowledge_base():
    """
    Creates a JSON-based knowledge base containing common IT support solutions.
    
    The knowledge base includes:
    - Issue categories (Hardware, Access, Software, Security, Email)
    - Search keywords for matching user queries
    - Step-by-step troubleshooting solutions
    
    Output:
        Creates/overwrites data/knowledge_base.json with 5 sample entries.
    """
    kb_data = [
        {
            "id": 101,
            "category": "Hardware",
            "issue": "Printer not responding or printing",
            "keywords": ["printer", "print", "paper", "jam", "offline"],
            "solution": (
                "1. Check if the printer is turned on and connected to the network.\n"
                "2. Restart the printer.\n"
                "3. Clear the print queue on your computer.\n"
                "4. Check for paper jams."
            )
        },
        {
            "id": 102,
            "category": "Access",
            "issue": "VPN Connection Failed",
            "keywords": ["vpn", "connection", "network", "remote", "access"],
            "solution": (
                "1. Ensure you have an active internet connection.\n"
                "2. Verify your MFA token is correct.\n"
                "3. Try switching the VPN protocol in settings to TCP.\n"
                "4. Reinstall the VPN client if the issue persists."
            )
        },
        {
            "id": 103,
            "category": "Software",
            "issue": "Application crashing on startup",
            "keywords": ["crash", "app", "software", "freeze", "close"],
            "solution": (
                "1. Check for software updates.\n"
                "2. Clear the application cache/temporary files.\n"
                "3. Restart your computer.\n"
                "4. If critical, request a reinstall via ticket."
            )
        },
        {
            "id": 104,
            "category": "Security",
            "issue": "Password Reset Instructions",
            "keywords": ["password", "reset", "login", "forgot", "account"],
            "solution": (
                "1. Go to the self-service portal at portal.company.com.\n"
                "2. Click 'Forgot Password'.\n"
                "3. Enter your employee ID.\n"
                "4. Follow the SMS verification steps."
            )
        },
        {
            "id": 105,
            "category": "Email",
            "issue": "Outlook not syncing",
            "keywords": ["email", "outlook", "sync", "receiving", "sending"],
            "solution": (
                "1. Check internet connection.\n"
                "2. Look for the 'Working Offline' toggle in the Send/Receive tab and turn it off.\n"
                "3. Close and reopen Outlook."
            )
        }
    ]

    with open(KB_FILE, 'w', encoding='utf-8') as f:
        json.dump(kb_data, f, indent=4)
    
    print(f"✅ [OK] Knowledge Base created/reset: {KB_FILE}")


# --- 2. GENERATE TICKETS DATABASE (SQLite) ---
def create_ticket_db():
    """
    Creates a SQLite database for managing support tickets.
    
    Schema:
        - id: Primary key (auto-increment)
        - user_id: User identifier (TEXT)
        - issue_summary: Brief description of the problem (TEXT)
        - priority: Low/Normal/High (TEXT with CHECK constraint)
        - status: Open/In Progress/Closed (TEXT with CHECK constraint)
        - created_at: Timestamp (automatic)
    
    Output:
        Creates data/tickets.db with sample seed data.
    """
    # Remove old database if it exists (factory reset)
    if os.path.exists(TICKETS_DB_FILE):
        os.remove(TICKETS_DB_FILE)
        print(f"🗑️  [OK] Deleted old Tickets DB: {TICKETS_DB_FILE}")

    conn = sqlite3.connect(TICKETS_DB_FILE)
    cursor = conn.cursor()

    # Create tickets table
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

    # Insert sample data (seed data for testing)
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
    print(f"✅ [OK] Ticket Database created: {TICKETS_DB_FILE}")


# --- 3. RESET SESSIONS DATABASE (Memory) ---
def reset_session_db():
    """
    Deletes the session database to provide a clean state for development.
    
    This is useful for:
    - Resetting conversation history during testing
    - Clearing stale session data
    - Starting fresh after schema changes
    
    Note:
        In production, sessions should persist. This function is for development only.
    """
    if os.path.exists(SESSIONS_DB_FILE):
        try:
            os.remove(SESSIONS_DB_FILE)
            print(f"✅ [OK] Deleted Session Memory: {SESSIONS_DB_FILE}")
        except OSError as e:
            print(f"⚠️  [WARN] Could not delete sessions DB (maybe in use?): {e}")
    else:
        print("[INFO] No session DB found to delete.")


if __name__ == "__main__":
    print("=" * 60)
    print("✈️  SupportPilot Data Layer Initialization")
    print("=" * 60)
    
    create_knowledge_base()
    create_ticket_db()
    reset_session_db()
    
    print("=" * 60)
    print("✅ Setup Complete - Ready to launch SupportPilot!")
    print("=" * 60)