"""
Observability Infrastructure

Provides tracing, logging, and metrics collection for the multi-agent system.
This is critical for debugging agent decisions and measuring L1 vs L2 performance.
"""

import logging
import structlog
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4


# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


@dataclass
class TraceModel:
    """
    Unified tracing model for tracking requests across the multi-agent system.
    
    Each user request gets a unique trace_id that follows the request through
    all agent interactions, enabling full observability of the decision flow.
    
    Attributes:
        trace_id: Unique UUID for this request
        user_id: User making the request
        timestamp: When the trace started
        agent_flow: Ordered list of agents that processed this request
        decision_points: Critical decisions made during processing
        metrics: Performance and outcome metrics
        start_time: For calculating response time
    
    Usage:
        trace = TraceModel.create(user_id="user_123")
        trace.log_agent("OrchestratorAgent")
        trace.log_decision("Route to KnowledgeAgent", "Intent: resolve_faq")
        trace.finalize(outcome="L1_RESOLVED")
    """
    trace_id: str
    user_id: str
    timestamp: datetime
    agent_flow: List[str] = field(default_factory=list)
    decision_points: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def create(cls, user_id: str) -> 'TraceModel':
        """
        Factory method to create a new trace with auto-generated UUID.
        
        Args:
            user_id: Identifier for the user making the request
            
        Returns:
            TraceModel: New trace instance ready for logging
        """
        trace_id = str(uuid4())
        logger.info(
            "trace_created",
            trace_id=trace_id,
            user_id=user_id
        )
        return cls(
            trace_id=trace_id,
            user_id=user_id,
            timestamp=datetime.now()
        )
    
    def log_agent(self, agent_name: str):
        """
        Record that a specific agent was invoked.
        
        Args:
            agent_name: Name of the agent (e.g., "KnowledgeAgent")
        """
        self.agent_flow.append(agent_name)
        logger.info(
            "agent_invoked",
            trace_id=self.trace_id,
            agent=agent_name,
            flow_position=len(self.agent_flow)
        )
    
    def log_decision(self, decision: str, reason: str, context: Optional[Dict] = None):
        """
        Record a critical decision point for debugging.
        
        Args:
            decision: What action was taken (e.g., "Escalate to L2")
            reason: Why this decision was made
            context: Additional metadata about the decision
        """
        decision_entry = {
            "decision": decision,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
        self.decision_points.append(decision_entry)
        
        logger.info(
            "decision_made",
            trace_id=self.trace_id,
            decision=decision,
            reason=reason,
            context=context
        )
    
    def log_tool_call(self, tool_name: str, input_params: Dict, output: Any):
        """
        Record tool execution for debugging.
        
        Args:
            tool_name: Name of the tool executed
            input_params: Parameters passed to the tool
            output: Result returned by the tool
        """
        logger.info(
            "tool_executed",
            trace_id=self.trace_id,
            tool=tool_name,
            input=input_params,
            output_preview=str(output)[:200]  # Truncate for readability
        )
    
    def finalize(self, outcome: str, resolution_level: Optional[int] = None):
        """
        Mark the trace as complete and record final metrics.
        
        Args:
            outcome: Final result (e.g., "L1_RESOLVED", "L2_ESCALATED")
            resolution_level: 1 for KB resolution, 2 for ticket creation
        """
        end_time = datetime.now()
        response_time = (end_time - self.start_time).total_seconds()
        
        self.metrics.update({
            "outcome": outcome,
            "resolution_level": resolution_level,
            "response_time_seconds": response_time,
            "total_agents": len(self.agent_flow),
            "decision_count": len(self.decision_points)
        })
        
        logger.info(
            "trace_completed",
            trace_id=self.trace_id,
            outcome=outcome,
            response_time=response_time,
            agent_flow=" → ".join(self.agent_flow)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize trace for storage or analysis"""
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_flow": self.agent_flow,
            "decision_points": self.decision_points,
            "metrics": self.metrics
        }


@dataclass
class MetricsCollector:
    """
    Aggregates metrics across all traces for performance monitoring.
    
    Key Metrics:
        - L1 Resolution Rate: % of issues resolved via Knowledge Base
        - L2 Escalation Rate: % of issues requiring ticket creation
        - Average Response Time: Mean time to respond to user
        - Negative Signal Rate: % of conversations with dissatisfaction
    """
    total_requests: int = 0
    l1_resolutions: int = 0
    l2_escalations: int = 0
    total_response_time: float = 0.0
    negative_signals_detected: int = 0
    
    def record_resolution(self, level: int, response_time: float, had_negative_signal: bool = False):
        """
        Record a completed request.
        
        Args:
            level: 1 for KB resolution, 2 for ticket escalation
            response_time: Time taken to respond (seconds)
            had_negative_signal: Whether user expressed dissatisfaction
        """
        self.total_requests += 1
        self.total_response_time += response_time
        
        if level == 1:
            self.l1_resolutions += 1
        elif level == 2:
            self.l2_escalations += 1
        
        if had_negative_signal:
            self.negative_signals_detected += 1
        
        logger.info(
            "metrics_updated",
            total_requests=self.total_requests,
            l1_rate=self.get_l1_rate(),
            l2_rate=self.get_l2_rate()
        )
    
    def get_l1_rate(self) -> float:
        """Calculate L1 resolution rate (0.0 to 1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.l1_resolutions / self.total_requests
    
    def get_l2_rate(self) -> float:
        """Calculate L2 escalation rate (0.0 to 1.0)"""
        if self.total_requests == 0:
            return 0.0
        return self.l2_escalations / self.total_requests
    
    def get_avg_response_time(self) -> float:
        """Calculate average response time in seconds"""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests
    
    def get_report(self) -> str:
        """Generate a human-readable metrics report"""
        return f"""
╔═══════════════════════════════════════╗
║     SupportPilot Metrics Report       ║
╚═══════════════════════════════════════╝

Total Requests: {self.total_requests}

Resolution Breakdown:
  • L1 (Knowledge Base): {self.l1_resolutions} ({self.get_l1_rate():.1%})
  • L2 (Ticket Created): {self.l2_escalations} ({self.get_l2_rate():.1%})

Performance:
  • Avg Response Time: {self.get_avg_response_time():.2f}s
  
User Satisfaction:
  • Negative Signals: {self.negative_signals_detected}
        """.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export metrics for analysis"""
        return {
            "total_requests": self.total_requests,
            "l1_resolutions": self.l1_resolutions,
            "l2_escalations": self.l2_escalations,
            "l1_rate": self.get_l1_rate(),
            "l2_rate": self.get_l2_rate(),
            "avg_response_time": self.get_avg_response_time(),
            "negative_signals_detected": self.negative_signals_detected
        }


# Global metrics instance (singleton pattern)
metrics_collector = MetricsCollector()