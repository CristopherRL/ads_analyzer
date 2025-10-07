# === File: src/agent/memory.py ===

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain_openai import AzureChatOpenAI


from src.database import get_db
from src.models import ConversationHistory
from src.utils.cost_calculator import CostCalculator
from config import (
    AZURE_OPENAI_ENDPOINT, 
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT_NAME, 
    AZURE_API_VERSION,
    MEMORY_TEMPERATURE, 
    MEMORY_MAX_TOKEN_LIMIT
)
from src.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseConversationMemory:
    """
    Custom memory class that uses ConversationSummaryBufferMemory internally
    and persists conversation history in PostgreSQL database.
    """
    
    def __init__(self, user_id: int, session_id: Optional[str] = None, llm=None, **kwargs):
        """
        Initialize database-backed conversation memory.
        
        Args:
            user_id: User ID (foreign key to users table)
            session_id: Optional session identifier for conversation continuity
            llm: Optional LLM instance to use for summarization
            **kwargs: Additional arguments for ConversationSummaryBufferMemory
        """
        # Store user_id and session_id as instance attributes
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        
        # Use provided LLM or create new one
        if llm is not None:
            self._llm = llm
        else:
            # Initialize Azure OpenAI LLM for summarization
            self._llm = AzureChatOpenAI(
                azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use deployment name
                api_key=AZURE_OPENAI_API_KEY,
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_version=AZURE_API_VERSION,
                temperature=MEMORY_TEMPERATURE,  # Configurable temperature for consistent summarization
                model=AZURE_OPENAI_DEPLOYMENT_NAME  # Required for token counting
            )
        
        # Initialize internal memory using composition instead of inheritance
        self._memory = ConversationSummaryBufferMemory(
            llm=self._llm,
            max_token_limit=MEMORY_MAX_TOKEN_LIMIT,  # Configurable token limit for summarization
            return_messages=True,
            **kwargs
        )
        
        # Load existing conversation history and long-term memory
        self._load_conversation_history()
        self._load_long_term_memory()
        
        logger.info(f"Initialized memory for user {user_id}, session {self.session_id}")
    
    def _load_conversation_history(self) -> None:
        """
        Load existing conversation history from database.
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Query conversation history for this user and session
            conversations = db.query(ConversationHistory).filter(
                and_(
                    ConversationHistory.user_id == self.user_id,
                    ConversationHistory.session_id == self.session_id
                )
            ).order_by(ConversationHistory.timestamp.asc()).all()
            
            # Convert database records to LangChain messages
            messages = []
            for conv in conversations:
                if conv.user_prompt:
                    messages.append(HumanMessage(content=conv.user_prompt))
                if conv.llm_response:
                    messages.append(AIMessage(content=conv.llm_response))
            
            # Load messages into memory
            if messages:
                self._memory.chat_memory.messages = messages
                logger.info(f"Loaded {len(conversations)} conversation pairs from database")
            else:
                logger.info("No previous conversation history found")
                
        except Exception as e:
            logger.error(f"Error loading conversation history: {e}")
        finally:
            if 'db' in locals():
                db.close()
    
    def _load_long_term_memory(self) -> None:
        """
        Load long-term memory from previous sessions for this user.
        This provides context from past conversations when starting a new session.
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Get recent conversation summaries from other sessions
            # Look for sessions from the last 7 days, excluding current session
            from datetime import datetime, timedelta
            week_ago = datetime.now() - timedelta(days=7)
            
            # Query for recent sessions with conversation data
            recent_sessions = db.query(ConversationHistory).filter(
                and_(
                    ConversationHistory.user_id == self.user_id,
                    ConversationHistory.session_id != self.session_id,
                    ConversationHistory.timestamp >= week_ago
                )
            ).order_by(ConversationHistory.timestamp.desc()).limit(5).all()
            
            if recent_sessions:
                # Create a summary of recent conversations
                session_summaries = []
                current_session = None
                
                for conv in recent_sessions:
                    if conv.session_id != current_session:
                        if current_session:
                            session_summaries.append(f"Sesión {current_session}: {len(session_messages)} mensajes")
                        current_session = conv.session_id
                        session_messages = []
                    
                    if conv.user_prompt:
                        session_messages.append(f"Usuario: {conv.user_prompt[:100]}...")
                    if conv.llm_response:
                        session_messages.append(f"Asistente: {conv.llm_response[:100]}...")
                
                # Add the last session
                if current_session:
                    session_summaries.append(f"Sesión {current_session}: {len(session_messages)} mensajes")
                
                # Create long-term memory context
                if session_summaries:
                    long_term_context = f"Contexto de conversaciones recientes: {'; '.join(session_summaries)}"
                    
                    # Add as a system message to provide context
                    from langchain.schema import SystemMessage
                    system_message = SystemMessage(content=long_term_context)
                    self._memory.chat_memory.messages.insert(0, system_message)
                    
                    logger.info(f"Loaded long-term memory context: {len(session_summaries)} recent sessions")
                else:
                    logger.info("No recent sessions found for long-term memory")
            else:
                logger.info("No previous conversations found for this user")
                
        except Exception as e:
            logger.error(f"Error loading long-term memory: {e}")
        finally:
            if 'db' in locals():
                db.close()
    
    def _save_conversation_pair(self, human_message: str, ai_message: str, 
                               full_prompt_sent: str = None, llm_params: dict = None) -> None:
        """
        Save a conversation pair (human message + AI response) to database with full tracking.
        
        Args:
            human_message: User's message
            ai_message: AI agent's response
            full_prompt_sent: Complete prompt sent to LLM (optional)
            llm_params: LLM parameters used (optional)
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Calculate token usage and cost
            tokens_used = 0
            estimated_cost = None
            
            if full_prompt_sent and ai_message:
                # Estimate tokens for input and output
                input_tokens = CostCalculator.estimate_tokens_from_text(full_prompt_sent)
                output_tokens = CostCalculator.estimate_tokens_from_text(ai_message)
                tokens_used = input_tokens + output_tokens
                
                # Calculate cost if we have model information
                model_name = 'default'
                if llm_params and 'model_name' in llm_params:
                    model_name = llm_params['model_name']
                
                estimated_cost = CostCalculator.calculate_cost(
                    input_tokens, output_tokens, model_name
                )
            
            # Create conversation history record with full tracking
            conversation = ConversationHistory(
                user_id=self.user_id,
                session_id=self.session_id,
                user_prompt=human_message,
                full_prompt_sent=full_prompt_sent,
                llm_response=ai_message,
                llm_params=llm_params,
                tokens_used=tokens_used,
                estimated_cost_usd=estimated_cost,
                timestamp=datetime.now()
            )
            
            db.add(conversation)
            db.commit()
            
            logger.info(f"Saved conversation pair to database for session {self.session_id} (tokens: {tokens_used}, cost: ${estimated_cost})")
            
        except Exception as e:
            logger.error(f"Error saving conversation to database: {e}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary with session information
        """
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "message_count": len(self._memory.chat_memory.messages),
            "has_summary": bool(self._memory.moving_summary_buffer)
        }
    
    def clear_session(self) -> None:
        """
        Clear current session memory (both in-memory and database).
        """
        try:
            # Clear in-memory state
            self._memory.clear()
            
            # Clear database records for this session
            db_gen = get_db()
            db = next(db_gen)
            
            db.query(ConversationHistory).filter(
                and_(
                    ConversationHistory.user_id == self.user_id,
                    ConversationHistory.session_id == self.session_id
                )
            ).delete()
            
            db.commit()
            
            logger.info(f"Cleared session {self.session_id} for user {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.
        
        Returns:
            Conversation summary string
        """
        if self._memory.moving_summary_buffer:
            return self._memory.moving_summary_buffer
        else:
            return "No conversation summary available yet."
    
    def get_recent_messages(self, count: int = 5) -> List[BaseMessage]:
        """
        Get recent conversation messages.
        
        Args:
            count: Number of recent messages to return
        
        Returns:
            List of recent BaseMessage objects
        """
        return self._memory.chat_memory.messages[-count:] if self._memory.chat_memory.messages else []
    
    # === LangChain Memory Interface Methods ===
    
    @property
    def chat_memory(self):
        """Delegate to internal memory's chat_memory."""
        return self._memory.chat_memory
    
    @property
    def moving_summary_buffer(self):
        """Delegate to internal memory's moving_summary_buffer."""
        return self._memory.moving_summary_buffer
    
    def clear(self):
        """Clear the memory."""
        self._memory.clear()
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory variables."""
        return self._memory.load_memory_variables(inputs)
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str], 
                    full_prompt_sent: str = None, llm_params: dict = None) -> None:
        """Save context to both internal memory and database with full tracking."""
        # Call internal memory method to update in-memory state
        self._memory.save_context(inputs, outputs)
        
        # Extract messages for database storage
        human_message = inputs.get("input", "")
        ai_message = outputs.get("output", "")
        
        # Save to database with full tracking
        if human_message and ai_message:
            self._save_conversation_pair(human_message, ai_message, full_prompt_sent, llm_params)

# === Memory Factory Function ===

def create_memory(user_id: int, session_id: Optional[str] = None, llm=None) -> DatabaseConversationMemory:
    """
    Factory function to create a new database-backed conversation memory.
    
    Args:
        user_id: User ID (foreign key to users table)
        session_id: Optional session identifier
        llm: Optional LLM instance to use for summarization
    
    Returns:
        DatabaseConversationMemory instance
    """
    return DatabaseConversationMemory(user_id=user_id, session_id=session_id, llm=llm)
