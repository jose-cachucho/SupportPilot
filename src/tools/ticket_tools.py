import sqlite3
import os
from typing import Optional
# Import crucial da ADK para aceder ao estado da sessão
from google.adk.tools.tool_context import ToolContext

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'tickets.db')

def get_db_connection() -> sqlite3.Connection:
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_ticket(issue_summary: str, tool_context: ToolContext, user_id: Optional[str] = None, priority: str = "Normal") -> str:
    """
    Creates a new support ticket. Automatically detects the user_id from the session state if not provided.

    Args:
        issue_summary (str): A brief description of the technical issue.
        tool_context (ToolContext): The session context (injected automatically by ADK).
        user_id (str, optional): The unique identifier of the user. If None, attempts to read 'user_id' from session state.
        priority (str, optional): The priority level ('Low', 'Normal', 'High'). Defaults to "Normal".

    Returns:
        str: Success message with Ticket ID or error message.
    """
    # 1. Tentar obter o user_id dos argumentos ou do estado
    #real_user_id = user_id or tool_context.state.get("user_id")
    # Tenta ler user:user_id (novo padrão) OU user_id (legado/argumento)
    real_user_id = user_id or tool_context.state.get("user:user_id") or tool_context.state.get("user_id")

    if not real_user_id:
        return "Error: Could not identify the user. Please provide a user_id explicitly."

    #print(f"[DEBUG] create_ticket called for user: {real_user_id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO tickets (user_id, issue_summary, priority, status) VALUES (?, ?, ?, ?)",
            (real_user_id, issue_summary, priority, 'Open')
        )
        
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return f"Ticket created successfully. Ticket ID: {ticket_id}"
    except Exception as e:
        return f"Error creating ticket: {str(e)}"

def get_ticket_status(tool_context: ToolContext, user_id: Optional[str] = None) -> str:
    """
    Retrieves ticket status. Automatically detects the user_id from the session state if not provided.

    Args:
        tool_context (ToolContext): The session context (injected automatically by ADK).
        user_id (str, optional): The user ID. If None, reads 'user_id' from session state.

    Returns:
        str: A formatted report of the user's tickets.
    """
    # 1. Resolver User ID
    #real_user_id = user_id or tool_context.state.get("user_id")
    real_user_id = user_id or tool_context.state.get("user:user_id") or tool_context.state.get("user_id")

    if not real_user_id:
        return "Error: Could not identify the user."

    #print(f"[DEBUG] get_ticket_status called for user: {real_user_id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, issue_summary, status, created_at FROM tickets WHERE user_id = ? ORDER BY created_at DESC",
            (real_user_id,)
        )
        
        tickets = cursor.fetchall()
        conn.close()
        
        if not tickets:
            return f"No tickets found for user: {real_user_id}"
        
        report = [f"Found {len(tickets)} ticket(s) for user {real_user_id}:"]
        for t in tickets:
            line = f"- Ticket #{t['id']}: {t['status']} (Issue: {t['issue_summary']})"
            report.append(line)
            
        return "\n".join(report)
    except Exception as e:
        return f"Error retrieving tickets: {str(e)}"
    
def update_ticket_status(ticket_id: str, new_status: str) -> str:
    """
    Updates the status of an existing ticket.
    Useful for technicians to mark tickets as 'In Progress' or 'Closed'.

    Args:
        ticket_id (str): The ID of the ticket to update (e.g., "5").
        new_status (str): The new status. MUST be one of: 'Open', 'In Progress', 'Closed'.

    Returns:
        str: A confirmation message or an error.
    """
    # 1. Validar os estados permitidos (Case insensitive para robustez)
    valid_states = ['Open', 'In Progress', 'Closed']
    # Tenta encontrar o match correto ignorando maiúsculas/minúsculas
    matched_status = next((s for s in valid_states if s.lower() == new_status.lower()), None)

    if not matched_status:
        return f"Error: Invalid status '{new_status}'. Allowed statuses are: {', '.join(valid_states)}."

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 2. Verificar se o ticket existe
        cursor.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,))
        if not cursor.fetchone():
            conn.close()
            return f"Error: Ticket ID {ticket_id} not found."

        # 3. Atualizar
        cursor.execute(
            "UPDATE tickets SET status = ? WHERE id = ?",
            (matched_status, ticket_id)
        )
        conn.commit()
        conn.close()
        
        return f"Success: Ticket #{ticket_id} status updated to '{matched_status}'."

    except Exception as e:
        return f"Error updating ticket: {str(e)}"