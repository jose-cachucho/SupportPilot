"""
Session and State Management Models (ADK-Compatible)

This module defines metadata structures that complement ADK's native
session management with SupportPilot-specific tracking.

ADK handles: conversation history, persistence
We handle: business logic state (kb_attempted, escalation tracking, etc.)
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class IntentType(Enum):
    """Classification of user intent by the Orchestrator"""
    RESOLVE_FAQ = "resolve_faq"      # Technical problems → Knowledge Agent
    CREATE_TICKET = "create_ticket"   # Explicit ticket request → Creation Agent
    CHECK_STATUS = "check_status"     # Query tickets → Query Agent
    UNKNOWN = "unknown"               # Fallback


class AgentType(Enum):
    """Available agents in the system"""
    ORCHESTRATOR = "OrchestratorAgent"
    KNOWLEDGE = "KnowledgeAgent"
    CREATION = "CreationAgent"
    QUERY = "QueryAgent"


@dataclass
class SessionMetadata:
    """
    Custom metadata for SupportPilot sessions.
    
    This complements ADK's native session management with business logic state
    that's specific to our multi-agent support system.
    
    ADK automatically handles:
    - Conversation history (messages)
    - Session persistence (if using DatabaseSessionService)
    - User/App/Session IDs
    
    We manually track:
    - Whether KB resolution was attempted
    - Whether escalation occurred
    - Negative signals count
    - Current problem being discussed
    - Last classified intent
    
    This metadata is stored as JSON in ADK session's custom fields.
    
    Attributes:
        trace_id: Unique identifier for observability (links to TraceModel)
        kb_attempted: Whether Knowledge Agent has been invoked
        escalated: Whether ticket has been created
        current_problem: Active issue being discussed
        last_intent: Most recent intent classification
        negative_signals_count: Number of dissatisfaction signals detected
        created_at: When this metadata was initialized
        last_updated: Last modification timestamp
    """
    trace_id: str
    kb_attempted: bool = False
    escalated: bool = False
    current_problem: str = ""
    last_intent: Optional[str] = None  # Store as string for JSON serialization
    negative_signals_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for storage in ADK session.
        
        Returns:
            Dict: JSON-serializable metadata
        """
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetadata':
        """
        Deserialize from dictionary loaded from ADK session.
        
        Args:
            data: Dictionary from ADK session metadata
            
        Returns:
            SessionMetadata: Reconstructed metadata object
        """
        # Convert ISO strings back to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('last_updated'), str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        
        return cls(**data)
    
    def update(self):
        """Update the last_updated timestamp"""
        self.last_updated = datetime.now()
    
    def mark_kb_attempted(self):
        """Mark that Knowledge Agent has been invoked"""
        self.kb_attempted = True
        self.update()
    
    def mark_escalated(self):
        """Mark that ticket has been created"""
        self.escalated = True
        self.update()
    
    def increment_negative_signals(self):
        """Increment dissatisfaction counter"""
        self.negative_signals_count += 1
        self.update()
    
    def set_current_problem(self, problem: str):
        """Update the current problem being discussed"""
        if not self.current_problem:  # Only set if not already set
            self.current_problem = problem
            self.update()
    
    def set_intent(self, intent: IntentType):
        """Update last intent classification"""
        self.last_intent = intent.value
        self.update()


@dataclass
class DecisionPoint:
    """
    Records a decision made by the Orchestrator for observability.
    
    This is separate from session state and is used purely for
    tracing/debugging the agent's decision-making process.
    
    Attributes:
        decision: What action was taken (e.g., "Route to KnowledgeAgent")
        reason: Why this decision was made
        timestamp: When the decision occurred
        context: Additional metadata (optional)
    """
    decision: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


# Helper functions for ADK integration

def create_initial_metadata(trace_id: str) -> SessionMetadata:
    """
    Create initial metadata for a new session.
    
    Args:
        trace_id: Unique trace ID from TraceModel
        
    Returns:
        SessionMetadata: Fresh metadata object
    """
    return SessionMetadata(trace_id=trace_id)


def extract_metadata_from_session(session: Any) -> Optional[SessionMetadata]:
    """
    Extract SessionMetadata from an ADK session object.
    
    ADK sessions can store custom metadata. This function retrieves
    our SupportPilot-specific metadata if it exists.
    
    Args:
        session: ADK Session object
        
    Returns:
        SessionMetadata or None: Extracted metadata if exists
    """
    # ADK sessions have a metadata field for custom data
    if hasattr(session, 'metadata') and session.metadata:
        try:
            return SessionMetadata.from_dict(session.metadata)
        except (KeyError, TypeError):
            return None
    return None


def update_session_metadata(session: Any, metadata: SessionMetadata):
    """
    Update ADK session with our custom metadata.
    
    Args:
        session: ADK Session object
        metadata: Our custom metadata to store
    """
    if hasattr(session, 'metadata'):
        session.metadata = metadata.to_dict()