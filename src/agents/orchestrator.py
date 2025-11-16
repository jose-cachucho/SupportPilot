"""
Orchestrator Agent - The Brain of SupportPilot (Full ADK)

This is the main coordinating agent that:
1. Receives all user inputs
2. Classifies user intent (rule-based for reliability)
3. Detects dissatisfaction signals
4. Delegates to specialized agents (Knowledge, Creation, Query)
5. Manages session state

Note: Orchestrator uses rule-based routing (not LLM-based) for predictability.
"""

import os
from typing import Optional, Dict, Any

from src.models.session import (
    SessionMetadata, 
    IntentType, 
    AgentType,
    create_initial_metadata
)
from src.core.observability import TraceModel, logger, metrics_collector
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.creation_agent import CreationAgent
from src.agents.query_agent import QueryAgent


class OrchestratorAgent:
    """
    Main orchestrating agent - coordinates the multi-agent system.
    
    Unlike the specialized agents, the Orchestrator uses rule-based logic
    for intent classification (for reliability) but delegates execution
    to LLM-powered specialized agents.
    
    Attributes:
        knowledge_agent: Specialized agent for KB resolution
        creation_agent: Specialized agent for ticket creation
        query_agent: Specialized agent for ticket status
        sessions: In-memory session metadata storage
    """
    
    # Negative signal patterns for detecting user dissatisfaction
    NEGATIVE_SIGNALS = [
        "didn't work", "doesn't work", "not working",
        "didn't help", "doesn't help",
        "still not", "still broken", "still having",
        "problem persists", "issue persists",
        "same error", "same problem",
        "not fixed", "not solved",
        "getting worse", "even worse",
        "talk to someone", "speak to human",
        "escalate", "this is useless", "waste of time"
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model_name: str = "gemini-2.0-flash-exp"
    ):
        """
        Initialize the Orchestrator Agent and all specialized agents.
        
        Args:
            api_key: Google AI API key
            model_name: Gemini model to use for all agents
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY must be set in environment or passed to constructor")
        
        os.environ["GOOGLE_API_KEY"] = self.api_key
        
        self.model_name = model_name
        
        # Initialize specialized agents (all use Full ADK)
        self.knowledge_agent = KnowledgeAgent(api_key=self.api_key, model_name=model_name)
        self.creation_agent = CreationAgent(api_key=self.api_key, model_name=model_name)
        self.query_agent = QueryAgent(api_key=self.api_key, model_name=model_name)
        
        # In-memory session metadata storage
        self.sessions: Dict[str, SessionMetadata] = {}
        
        logger.info("orchestrator_initialized", model=model_name)
    
    def get_or_create_metadata(self, user_id: str) -> SessionMetadata:
        """
        Get existing metadata or create new session.
        
        Args:
            user_id: User identifier
            
        Returns:
            SessionMetadata: Active metadata for this user
        """
        if user_id not in self.sessions:
            trace = TraceModel.create(user_id)
            self.sessions[user_id] = create_initial_metadata(trace.trace_id)
            logger.info(
                "session_metadata_created",
                user_id=user_id,
                trace_id=trace.trace_id
            )
        
        return self.sessions[user_id]
    
    def detect_dissatisfaction(self, message: str) -> bool:
        """
        Detect if user is expressing dissatisfaction.
        
        Uses keyword matching for MVP reliability.
        
        Args:
            message: User's message
            
        Returns:
            bool: True if dissatisfaction detected
        """
        message_lower = message.lower()
        
        for signal in self.NEGATIVE_SIGNALS:
            if signal in message_lower:
                logger.info(
                    "negative_signal_detected",
                    signal=signal,
                    message_preview=message[:100]
                )
                return True
        
        return False
    
    def classify_intent(self, message: str, metadata: SessionMetadata) -> IntentType:
        """
        Classify user's intent to determine which agent to invoke.
        
        Uses rule-based classification for reliability.
        
        Args:
            message: User's message
            metadata: Current session metadata
            
        Returns:
            IntentType: Classified intent
        """
        message_lower = message.lower()
        
        # Priority 1: Explicit ticket requests
        ticket_keywords = [
            "create ticket", "open ticket", "new ticket",
            "need help", "escalate", "speak to someone", 
            "talk to support", "contact support"
        ]
        if any(kw in message_lower for kw in ticket_keywords):
            return IntentType.CREATE_TICKET
        
        # Priority 2: Status checks
        status_keywords = [
            "my tickets", "ticket status", "check ticket", 
            "ticket number", "open tickets", "check status",
            "ticket id", "what are my"
        ]
        if any(kw in message_lower for kw in status_keywords):
            return IntentType.CHECK_STATUS
        
        # Priority 3: Auto-escalation if KB already attempted and user dissatisfied
        if metadata.kb_attempted and self.detect_dissatisfaction(message):
            return IntentType.CREATE_TICKET
        
        # Default: Try to resolve via KB
        return IntentType.RESOLVE_FAQ
    
    def process_message(self, user_id: str, message: str) -> str:
        """
        Main entry point: Process a user message and return response.
        
        Orchestration flow:
        1. Get/create session metadata
        2. Create trace for observability
        3. Classify intent (rule-based)
        4. Detect dissatisfaction
        5. DELEGATE to appropriate specialized agent (LLM-powered)
        6. Update state and metrics
        7. Return formatted response
        
        Args:
            user_id: User identifier
            message: User's message
            
        Returns:
            str: Agent's response
        """
        # Get session metadata
        metadata = self.get_or_create_metadata(user_id)
        
        # Create trace
        trace = TraceModel.create(user_id)
        trace.log_agent(AgentType.ORCHESTRATOR.value)
        
        # Classify intent
        intent = self.classify_intent(message, metadata)
        metadata.set_intent(intent)
        
        trace.log_decision(
            decision=f"Classified intent as {intent.value}",
            reason=f"Based on keywords (kb_attempted={metadata.kb_attempted})",
            context={"message_preview": message[:100]}
        )
        
        # Detect dissatisfaction
        is_dissatisfied = self.detect_dissatisfaction(message)
        if is_dissatisfied:
            metadata.increment_negative_signals()
            trace.log_decision(
                decision="Negative signal detected",
                reason="User expressed dissatisfaction",
                context={"count": metadata.negative_signals_count}
            )
        
        try:
            # Route to appropriate agent
            if intent == IntentType.RESOLVE_FAQ:
                response = self._handle_faq_resolution(
                    metadata, message, trace, user_id
                )
                
            elif intent == IntentType.CREATE_TICKET:
                context = None
                if metadata.kb_attempted and is_dissatisfied:
                    context = "Knowledge base solution was attempted but unsuccessful"
                response = self._handle_ticket_creation(
                    metadata, message, trace, user_id, context
                )
                
            elif intent == IntentType.CHECK_STATUS:
                response = self._handle_status_query(
                    metadata, trace, user_id
                )
                
            else:
                response = "I'm not sure how to help with that. Could you rephrase your request?"
            
            # Update metrics
            resolution_level = 2 if metadata.escalated else 1
            metrics_collector.record_resolution(
                level=resolution_level,
                response_time=0.0,
                had_negative_signal=metadata.negative_signals_count > 0
            )
            
            # Finalize trace
            if metadata.escalated:
                trace.finalize("L2_ESCALATED", resolution_level=2)
            else:
                trace.finalize("L1_ATTEMPTED", resolution_level=1)
            
            return response
            
        except Exception as e:
            logger.error("orchestrator_error", error=str(e), trace_id=trace.trace_id)
            return "I apologize, but I encountered an error. Please try again or contact IT support directly."
    
    def _handle_faq_resolution(
        self, 
        metadata: SessionMetadata, 
        message: str, 
        trace: TraceModel,
        user_id: str
    ) -> str:
        """Handle FAQ resolution by delegating to Knowledge Agent (LLM-powered)."""
        trace.log_decision(
            decision="Delegate to Knowledge Agent",
            reason="Attempting L1 resolution via knowledge base"
        )
        trace.log_agent(AgentType.KNOWLEDGE.value)
        
        # Delegate to Knowledge Agent (uses LLM + Runner)
        result = self.knowledge_agent.resolve(message, trace.trace_id)
        
        # Mark that KB was attempted
        metadata.mark_kb_attempted()
        
        # Check if resolution was successful
        if result["success"] and result["response"] != "KB_NOT_FOUND":
            trace.log_decision(
                decision="L1 Resolution Successful",
                reason="Knowledge Agent found solution in KB"
            )
            return result["response"]
        else:
            # Auto-escalate
            trace.log_decision(
                decision="Auto-escalate to L2",
                reason="Knowledge base has no solution"
            )
            return self._handle_ticket_creation(
                metadata, message, trace, user_id,
                context="Knowledge base search found no matching solution"
            )
    
    def _handle_ticket_creation(
        self,
        metadata: SessionMetadata,
        message: str,
        trace: TraceModel,
        user_id: str,
        context: Optional[str] = None
    ) -> str:
        """Handle ticket creation by delegating to Creation Agent (LLM-powered)."""
        trace.log_decision(
            decision="Delegate to Creation Agent",
            reason="Escalating to L2 support"
        )
        trace.log_agent(AgentType.CREATION.value)
        
        metadata.set_current_problem(message)
        
        # Delegate to Creation Agent (uses LLM + Runner)
        result = self.creation_agent.create_ticket(
            user_id=user_id,
            problem_description=metadata.current_problem,
            trace_id=trace.trace_id,
            context=context
        )
        
        if result["success"]:
            metadata.mark_escalated()
            trace.log_decision(
                decision="L2 Escalation Complete",
                reason=f"Ticket created: {result['ticket_id']}"
            )
        
        return result["response"]
    
    def _handle_status_query(
        self, 
        metadata: SessionMetadata, 
        trace: TraceModel,
        user_id: str
    ) -> str:
        """Handle status query by delegating to Query Agent (LLM-powered)."""
        trace.log_decision(
            decision="Delegate to Query Agent",
            reason="User requesting ticket status"
        )
        trace.log_agent(AgentType.QUERY.value)
        
        # Delegate to Query Agent (uses LLM + Runner)
        result = self.query_agent.query_tickets(user_id, trace.trace_id)
        
        return result["response"]