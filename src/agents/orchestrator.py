"""
Orchestrator Agent - The Brain of SupportPilot (ADK-Native)

This is the main coordinating agent that:
1. Uses ADK's SessionService for conversation management
2. Maintains custom metadata for business logic
3. Delegates to specialized agents
4. Manages escalation logic

This implementation properly integrates with the ADK framework.
"""

import os
from typing import Optional, Dict, Any
from google import genai
from google.genai import types

from src.models.session import (
    SessionMetadata, 
    IntentType, 
    AgentType,
    create_initial_metadata,
    extract_metadata_from_session,
    update_session_metadata
)
from src.core.observability import TraceModel, logger, metrics_collector
from src.agents.knowledge_agent import KnowledgeAgent
from src.agents.creation_agent import CreationAgent
from src.agents.query_agent import QueryAgent


class OrchestratorAgent:
    """
    Main orchestrating agent - coordinates the multi-agent system.
    
    Uses ADK patterns for session management while maintaining custom
    business logic for the support workflow.
    
    Attributes:
        api_key: Google AI API key
        model_name: Gemini model to use
        knowledge_agent: Specialized agent for KB resolution
        creation_agent: Specialized agent for ticket creation
        query_agent: Specialized agent for ticket status
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
            raise ValueError("GOOGLE_API_KEY must be set")
        
        self.model_name = model_name
        
        # Initialize specialized agents
        self.knowledge_agent = KnowledgeAgent(api_key=self.api_key, model_name=model_name)
        self.creation_agent = CreationAgent(api_key=self.api_key, model_name=model_name)
        self.query_agent = QueryAgent(api_key=self.api_key, model_name=model_name)
        
        logger.info("orchestrator_initialized", model=model_name)
    
    def get_or_create_metadata(self, session: Any) -> SessionMetadata:
        """
        Get existing metadata from ADK session or create new.
        
        Args:
            session: ADK Session object
            
        Returns:
            SessionMetadata: Active metadata for this session
        """
        metadata = extract_metadata_from_session(session)
        
        if metadata is None:
            # Create new metadata
            trace = TraceModel.create(user_id=session.user_id if hasattr(session, 'user_id') else "unknown")
            metadata = create_initial_metadata(trace.trace_id)
            update_session_metadata(session, metadata)
            logger.info(
                "session_metadata_created",
                session_id=getattr(session, 'id', 'unknown'),
                trace_id=metadata.trace_id
            )
        
        return metadata
    
    def detect_dissatisfaction(self, message: str) -> bool:
        """
        Detect if user is expressing dissatisfaction.
        
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
        
        Args:
            message: User's message
            metadata: Current session metadata
            
        Returns:
            IntentType: Classified intent
        """
        message_lower = message.lower()
        
        # Priority 1: Explicit ticket requests
        ticket_keywords = [
            "create ticket", "open ticket", "need help", 
            "escalate", "speak to someone", "talk to support"
        ]
        if any(kw in message_lower for kw in ticket_keywords):
            return IntentType.CREATE_TICKET
        
        # Priority 2: Status checks
        status_keywords = [
            "my tickets", "ticket status", "check ticket", 
            "ticket number", "open tickets", "check status"
        ]
        if any(kw in message_lower for kw in status_keywords):
            return IntentType.CHECK_STATUS
        
        # Priority 3: Auto-escalation if KB already attempted and user dissatisfied
        if metadata.kb_attempted and self.detect_dissatisfaction(message):
            return IntentType.CREATE_TICKET
        
        # Default: Try to resolve via KB (Knowledge Agent)
        return IntentType.RESOLVE_FAQ
    
    async def process_message_async(
        self,
        user_id: str,
        session_id: str,
        message: str,
        session_service: Any
    ) -> str:
        """
        Process message using ADK session service (async version).
        
        This is the ADK-native way of handling messages with proper
        session management.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            message: User's message
            session_service: ADK SessionService instance
            
        Returns:
            str: Agent's response
        """
        # Get or create ADK session
        try:
            session = await session_service.get_session(
                app_name="SupportPilot",
                user_id=user_id,
                session_id=session_id
            )
        except:
            session = await session_service.create_session(
                app_name="SupportPilot",
                user_id=user_id,
                session_id=session_id
            )
        
        # Get our custom metadata
        metadata = self.get_or_create_metadata(session)
        
        # Create trace
        trace = TraceModel.create(user_id)
        trace.log_agent(AgentType.ORCHESTRATOR.value)
        
        # Classify intent
        intent = self.classify_intent(message, metadata)
        metadata.set_intent(intent)
        
        trace.log_decision(
            decision=f"Classified intent as {intent.value}",
            reason=f"Based on message analysis and metadata (kb_attempted={metadata.kb_attempted})",
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
                response = self._handle_faq_resolution(metadata, message, trace, user_id)
                
            elif intent == IntentType.CREATE_TICKET:
                context = None
                if metadata.kb_attempted and is_dissatisfied:
                    context = "Knowledge base solution was attempted but unsuccessful"
                response = self._handle_ticket_creation(metadata, message, trace, user_id, context)
                
            elif intent == IntentType.CHECK_STATUS:
                response = self._handle_status_query(metadata, trace, user_id)
                
            else:
                response = "I'm not sure how to help with that. Could you rephrase?"
            
            # Update session metadata
            update_session_metadata(session, metadata)
            
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
            return "I apologize, but I encountered an error. Please try again."
    
    def process_message(self, user_id: str, message: str) -> str:
        """
        Synchronous wrapper for simple testing without ADK Runner.
        
        For production, use process_message_async with proper ADK integration.
        This version uses in-memory session simulation for MVP demos.
        
        Args:
            user_id: User identifier
            message: User's message
            
        Returns:
            str: Agent's response
        """
        # Simulate session with in-memory metadata
        if not hasattr(self, '_test_metadata_store'):
            self._test_metadata_store = {}
        
        if user_id not in self._test_metadata_store:
            trace = TraceModel.create(user_id)
            self._test_metadata_store[user_id] = create_initial_metadata(trace.trace_id)
        
        metadata = self._test_metadata_store[user_id]
        
        # Create trace
        trace = TraceModel.create(user_id)
        trace.log_agent(AgentType.ORCHESTRATOR.value)
        
        # Classify intent
        intent = self.classify_intent(message, metadata)
        metadata.set_intent(intent)
        
        trace.log_decision(
            decision=f"Classified intent as {intent.value}",
            reason=f"Based on message (kb_attempted={metadata.kb_attempted})"
        )
        
        # Detect dissatisfaction
        is_dissatisfied = self.detect_dissatisfaction(message)
        if is_dissatisfied:
            metadata.increment_negative_signals()
            trace.log_decision(
                decision="Negative signal detected",
                reason="User dissatisfaction"
            )
        
        try:
            # Route to agent
            if intent == IntentType.RESOLVE_FAQ:
                response = self._handle_faq_resolution(metadata, message, trace, user_id)
            elif intent == IntentType.CREATE_TICKET:
                context = "KB unsuccessful" if metadata.kb_attempted and is_dissatisfied else None
                response = self._handle_ticket_creation(metadata, message, trace, user_id, context)
            elif intent == IntentType.CHECK_STATUS:
                response = self._handle_status_query(metadata, trace, user_id)
            else:
                response = "Could you rephrase that?"
            
            # Metrics
            resolution_level = 2 if metadata.escalated else 1
            metrics_collector.record_resolution(
                level=resolution_level,
                response_time=0.0,
                had_negative_signal=metadata.negative_signals_count > 0
            )
            
            trace.finalize(
                "L2_ESCALATED" if metadata.escalated else "L1_ATTEMPTED",
                resolution_level=resolution_level
            )
            
            return response
            
        except Exception as e:
            logger.error("orchestrator_error", error=str(e))
            return "I encountered an error. Please try again."
    
    def _handle_faq_resolution(
        self, 
        metadata: SessionMetadata, 
        message: str, 
        trace: TraceModel,
        user_id: str
    ) -> str:
        """Handle FAQ resolution via Knowledge Agent."""
        trace.log_decision(
            decision="Delegate to Knowledge Agent",
            reason="Attempting L1 resolution"
        )
        trace.log_agent(AgentType.KNOWLEDGE.value)
        
        result = self.knowledge_agent.resolve(message, trace.trace_id)
        metadata.mark_kb_attempted()
        
        if result["success"] and result["response"] != "KB_NOT_FOUND":
            trace.log_decision(
                decision="L1 Resolution Successful",
                reason=f"KB article: {result.get('article_id')}"
            )
            return result["response"]
        else:
            # Auto-escalate
            trace.log_decision(
                decision="Auto-escalate to L2",
                reason="No KB solution found"
            )
            return self._handle_ticket_creation(
                metadata, message, trace, user_id,
                context="Knowledge base has no matching solution"
            )
    
    def _handle_ticket_creation(
        self,
        metadata: SessionMetadata,
        message: str,
        trace: TraceModel,
        user_id: str,
        context: Optional[str] = None
    ) -> str:
        """Handle ticket creation via Creation Agent."""
        trace.log_decision(
            decision="Delegate to Creation Agent",
            reason="Escalating to L2"
        )
        trace.log_agent(AgentType.CREATION.value)
        
        metadata.set_current_problem(message)
        
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
                reason=f"Ticket: {result['ticket_id']}"
            )
        
        return result["response"]
    
    def _handle_status_query(
        self, 
        metadata: SessionMetadata, 
        trace: TraceModel,
        user_id: str
    ) -> str:
        """Handle status query via Query Agent."""
        trace.log_decision(
            decision="Delegate to Query Agent",
            reason="User requesting ticket status"
        )
        trace.log_agent(AgentType.QUERY.value)
        
        result = self.query_agent.query_tickets(user_id, trace.trace_id)
        return result["response"]