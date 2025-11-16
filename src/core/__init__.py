"""
Core infrastructure: database, observability.

Database:
- Database: SQLite manager for tickets
- KnowledgeBase: JSON-based KB manager
- Singleton getters for easy access

Observability:
- TraceModel: Request tracing with UUID
- MetricsCollector: L1/L2 metrics aggregation
- logger: Structured logging (structlog)
"""

from src.core.database import (
    Database, 
    KnowledgeBase, 
    get_database, 
    get_knowledge_base
)
from src.core.observability import (
    TraceModel, 
    MetricsCollector, 
    metrics_collector, 
    logger
)

__all__ = [
    # Database
    "Database",
    "KnowledgeBase",
    "get_database",
    "get_knowledge_base",
    # Observability
    "TraceModel",
    "MetricsCollector",
    "metrics_collector",
    "logger"
]