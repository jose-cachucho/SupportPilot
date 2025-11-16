"""
Data models for sessions and state management.

SessionMetadata complements ADK's native session management with
SupportPilot-specific business logic tracking.

Available models:
- SessionMetadata: Custom metadata for business logic state
- IntentType: Enum for intent classification
- AgentType: Enum for agent identification
- DecisionPoint: Decision tracking for observability

Helper functions:
- create_initial_metadata: Factory for new sessions
- extract_metadata_from_session: Extract from ADK session (future)
- update_session_metadata: Update ADK session (future)
"""

from src.models.session import (
    SessionMetadata,
    IntentType,
    AgentType,
    DecisionPoint,
    create_initial_metadata,
    extract_metadata_from_session,
    update_session_metadata
)

__all__ = [
    "SessionMetadata",
    "IntentType",
    "AgentType",
    "DecisionPoint",
    "create_initial_metadata",
    "extract_metadata_from_session",
    "update_session_metadata"
]