"""
Database Layer for SupportPilot

Manages SQLite database for ticket storage and retrieval.
Provides clean interface for tools to interact with persistent data.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


class Database:
    """
    SQLite database manager for the service desk system.
    
    This class handles:
    - Database initialization and schema creation
    - Ticket CRUD operations
    - Query methods for ticket status
    
    Usage:
        db = Database("data/service_desk.db")
        ticket_id = db.create_ticket("user_123", "VPN issue", "TRACE-001")
        tickets = db.get_user_tickets("user_123")
    """
    
    def __init__(self, db_path: str = "data/service_desk.db"):
        """
        Initialize database connection and ensure schema exists.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self._init_schema()
    
    def _init_schema(self):
        """Create tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Tickets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'Open',
                priority TEXT DEFAULT 'Normal',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                trace_id TEXT,
                resolved_at DATETIME
            )
        """)
        
        # Index for faster user queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON tickets(user_id)
        """)
        
        self.conn.commit()
    
    def create_ticket(
        self, 
        user_id: str, 
        description: str, 
        trace_id: Optional[str] = None,
        priority: str = "Normal"
    ) -> str:
        """
        Create a new support ticket.
        
        Args:
            user_id: Identifier of the user creating the ticket
            description: Problem description (free text)
            trace_id: Optional trace ID for observability
            priority: Ticket priority ('Low', 'Normal', 'High')
            
        Returns:
            str: Formatted ticket ID (e.g., "TICKET-1001")
            
        Example:
            >>> db.create_ticket("user_123", "VPN connection failed", "trace-abc")
            "TICKET-1001"
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO tickets (user_id, description, trace_id, priority, status)
            VALUES (?, ?, ?, ?, 'Open')
        """, (user_id, description, trace_id, priority))
        
        self.conn.commit()
        ticket_id = cursor.lastrowid
        
        return f"TICKET-{ticket_id:04d}"
    
    def get_user_tickets(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all tickets for a specific user.
        
        Args:
            user_id: User identifier to filter by
            
        Returns:
            List[Dict]: List of ticket dictionaries, each containing:
                - ticket_id: Formatted ID (e.g., "TICKET-1001")
                - description: Problem description
                - status: Current status ('Open', 'In Progress', 'Closed')
                - priority: Priority level
                - created_at: Creation timestamp
                - updated_at: Last update timestamp
                
        Example:
            >>> db.get_user_tickets("user_123")
            [
                {
                    "ticket_id": "TICKET-1001",
                    "description": "VPN issue",
                    "status": "Open",
                    "priority": "Normal",
                    "created_at": "2025-11-15 10:30:00"
                }
            ]
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT ticket_id, description, status, priority, 
                   created_at, updated_at
            FROM tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        
        tickets = []
        for row in rows:
            tickets.append({
                "ticket_id": f"TICKET-{row['ticket_id']:04d}",
                "description": row["description"],
                "status": row["status"],
                "priority": row["priority"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        
        return tickets
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific ticket by its ID.
        
        Args:
            ticket_id: Formatted ticket ID (e.g., "TICKET-1001")
            
        Returns:
            Dict or None: Ticket details if found, None otherwise
        """
        # Extract numeric ID from formatted string
        numeric_id = int(ticket_id.replace("TICKET-", ""))
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ticket_id, user_id, description, status, priority,
                   created_at, updated_at, trace_id
            FROM tickets
            WHERE ticket_id = ?
        """, (numeric_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "ticket_id": f"TICKET-{row['ticket_id']:04d}",
            "user_id": row["user_id"],
            "description": row["description"],
            "status": row["status"],
            "priority": row["priority"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "trace_id": row["trace_id"]
        }
    
    def update_ticket_status(self, ticket_id: str, new_status: str):
        """
        Update the status of a ticket.
        
        Args:
            ticket_id: Formatted ticket ID
            new_status: New status ('Open', 'In Progress', 'Closed')
        """
        numeric_id = int(ticket_id.replace("TICKET-", ""))
        
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE tickets
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
        """, (new_status, numeric_id))
        
        self.conn.commit()
    
    def get_all_tickets(self) -> List[Dict[str, Any]]:
        """
        Retrieve all tickets (for admin/metrics purposes).
        
        Returns:
            List[Dict]: All tickets in the system
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ticket_id, user_id, description, status, 
                   created_at, trace_id
            FROM tickets
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class KnowledgeBase:
    """
    In-memory knowledge base loaded from JSON file.
    
    Provides FAQ search functionality using simple keyword matching.
    In production, this would use vector embeddings for semantic search.
    
    Usage:
        kb = KnowledgeBase("data/knowledge_base.json")
        result = kb.search("vpn not connecting")
    """
    
    def __init__(self, kb_path: str = "data/knowledge_base.json"):
        """
        Load knowledge base from JSON file.
        
        Args:
            kb_path: Path to knowledge_base.json file
        """
        self.kb_path = kb_path
        self.articles = []
        self._load_kb()
    
    def _load_kb(self):
        """Load and parse knowledge base JSON"""
        try:
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                self.articles = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Knowledge base not found at {self.kb_path}")
            self.articles = []
    
    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search for a solution in the knowledge base.
        
        Uses simple keyword matching. Returns the first article where
        any keyword matches the query (case-insensitive).
        
        Args:
            query: User's problem description (free text)
            
        Returns:
            Dict or None: Article with matching solution, or None if not found
                - id: Article identifier (e.g., "kb-001")
                - title: Article title
                - solution: Step-by-step solution
                - category: Problem category
                
        Example:
            >>> kb.search("vpn not working")
            {
                "id": "kb-001",
                "title": "VPN Connection Issues",
                "solution": "1. Restart router\n2. Check credentials...",
                "category": "network"
            }
        """
        query_lower = query.lower()
        
        for article in self.articles:
            # Check if any keyword matches the query
            keywords = article.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    return {
                        "id": article["id"],
                        "title": article["title"],
                        "solution": article["solution"],
                        "category": article.get("category", "general")
                    }
        
        return None
    
    def get_article_by_id(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific article by ID.
        
        Args:
            article_id: Article identifier (e.g., "kb-001")
            
        Returns:
            Dict or None: Article details if found
        """
        for article in self.articles:
            if article["id"] == article_id:
                return article
        return None
    
    def get_all_categories(self) -> List[str]:
        """Get list of all unique categories in KB"""
        categories = set()
        for article in self.articles:
            category = article.get("category", "general")
            categories.add(category)
        return sorted(list(categories))


# Singleton instances
_db_instance = None
_kb_instance = None


def get_database() -> Database:
    """Get or create the global Database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


def get_knowledge_base() -> KnowledgeBase:
    """Get or create the global KnowledgeBase instance"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance