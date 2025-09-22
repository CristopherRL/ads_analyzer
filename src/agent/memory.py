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
    
    def __init__(self, user_id: int, session_id: Optional[str] = None, **kwargs):
        """
        Initialize database-backed conversation memory.
        
        Args:
            user_id: User ID (foreign key to users table)
            session_id: Optional session identifier for conversation continuity
            **kwargs: Additional arguments for ConversationSummaryBufferMemory
        """
        # Store user_id and session_id as instance attributes
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        
        # Initialize Azure OpenAI LLM for summarization
        llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use deployment name
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_API_VERSION,
            temperature=MEMORY_TEMPERATURE,  # Configurable temperature for consistent summarization
            model=AZURE_OPENAI_DEPLOYMENT_NAME  # Required for token counting
        )
        
        # Initialize internal memory using composition instead of inheritance
        self._memory = ConversationSummaryBufferMemory(
            llm=llm,
            max_token_limit=MEMORY_MAX_TOKEN_LIMIT,  # Configurable token limit for summarization
            return_messages=True,
            **kwargs
        )
        
        # Load existing conversation history
        self._load_conversation_history()
        
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
    
    def _save_conversation_pair(self, human_message: str, ai_message: str) -> None:
        """
        Save a conversation pair (human message + AI response) to database.
        
        Args:
            human_message: User's message
            ai_message: AI agent's response
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Create conversation history record
            conversation = ConversationHistory(
                user_id=self.user_id,
                session_id=self.session_id,
                user_prompt=human_message,
                llm_response=ai_message,
                timestamp=datetime.now()
            )
            
            db.add(conversation)
            db.commit()
            
            logger.info(f"Saved conversation pair to database for session {self.session_id}")
            
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
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Save context to both internal memory and database."""
        # Call internal memory method to update in-memory state
        self._memory.save_context(inputs, outputs)
        
        # Extract messages for database storage
        human_message = inputs.get("input", "")
        ai_message = outputs.get("output", "")
        
        # Save to database
        if human_message and ai_message:
            self._save_conversation_pair(human_message, ai_message)

# === Memory Factory Function ===

def create_memory(user_id: int, session_id: Optional[str] = None) -> DatabaseConversationMemory:
    """
    Factory function to create a new database-backed conversation memory.
    
    Args:
        user_id: User ID (foreign key to users table)
        session_id: Optional session identifier
    
    Returns:
        DatabaseConversationMemory instance
    """
    return DatabaseConversationMemory(user_id=user_id, session_id=session_id)
