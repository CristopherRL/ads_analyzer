# === File: src/agent/agent_executor.py ===

from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage
from sqlalchemy import and_

from src.agent.memory import DatabaseConversationMemory, create_memory
from src.tools.facebook_tools import list_available_clients_tool, facebook_ads_analysis_tool
from config import (
    AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT_NAME, AZURE_API_VERSION,
    AGENT_TEMPERATURE, AGENT_MAX_TOKENS, AGENT_MAX_ITERATIONS,
    SYSTEM_PROMPT_SOURCE, DEFAULT_PROMPT_FILE
)
from src.logging_config import get_logger

logger = get_logger(__name__)

# === System Prompt Management ===

# === Agent Configuration ===

class DigitalMarketingAgent:
    """
    Digital Marketing Analysis Agent using LangChain.
    Provides conversational interface for Facebook Ads analysis.
    """
    
    def __init__(self, user_id: str, session_id: Optional[str] = None):
        """
        Initialize the Digital Marketing Agent.
        
        Args:
            user_id: User identifier (e.g., email)
            session_id: Optional session identifier for conversation continuity
        """
        self.user_id = user_id
        self.session_id = session_id or generate_session_id(user_id)
        
        # Initialize components
        self.llm = self._create_llm()
        self.memory = create_memory(user_id, self.session_id)
        self.tools = self._get_tools()
        self.agent = self._create_agent()
        self.agent_executor = self._create_agent_executor()
        
        logger.info(f"Initialized Digital Marketing Agent for user {user_id}")
    
    def _create_llm(self) -> ChatOpenAI:
        """
        Create and configure the Azure OpenAI LLM.
        
        Returns:
            Configured ChatOpenAI instance
        """
        return ChatOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_API_VERSION,
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
            temperature=AGENT_TEMPERATURE,  # Configurable temperature for balanced creativity
            model_name=AZURE_OPENAI_DEPLOYMENT_NAME,
            max_tokens=AGENT_MAX_TOKENS
        )
    
    def _get_tools(self) -> List:
        """
        Get list of available tools for the agent.
        
        Returns:
            List of LangChain tools
        """
        return [
            list_available_clients_tool,
            facebook_ads_analysis_tool
        ]
    
    def _get_system_prompt(self) -> str:
        """
        Get system prompt from configured source (file or database).
        
        Returns:
            System prompt string
        """
        if SYSTEM_PROMPT_SOURCE == 'database':
            return self._load_prompt_from_database()
        else:
            return self._load_prompt_from_file()
    
    def _load_prompt_from_file(self) -> str:
        """
        Load system prompt from default file.
        
        Returns:
            System prompt string
        """
        try:
            with open(DEFAULT_PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
            logger.info(f"Loaded system prompt from file: {DEFAULT_PROMPT_FILE}")
            return prompt
        except Exception as e:
            logger.error(f"Error loading prompt from file: {e}")
            # Fallback to hardcoded prompt
            return self._get_fallback_prompt()
    
    def _load_prompt_from_database(self) -> str:
        """
        Load active system prompt from database.
        
        Returns:
            System prompt string
        """
        try:
            from src.database import get_db
            from src.models import PromptVersion
            
            db_gen = get_db()
            db = next(db_gen)
            
            # Get active prompt version (assuming 'system' as prompt_name)
            active_prompt = db.query(PromptVersion).filter(
                and_(
                    PromptVersion.prompt_name == 'system',
                    PromptVersion.is_active == True
                )
            ).first()
            
            if active_prompt:
                logger.info(f"Loaded system prompt from database: {active_prompt.prompt_name} v{active_prompt.version}")
                return active_prompt.prompt_text
            else:
                logger.warning("No active prompt found in database, using file fallback")
                return self._load_prompt_from_file()
                
        except Exception as e:
            logger.error(f"Error loading prompt from database: {e}")
            return self._load_prompt_from_file()
        finally:
            if 'db' in locals():
                db.close()
    
    def _get_fallback_prompt(self) -> str:
        """
        Get fallback system prompt if all else fails.
        
        Returns:
            Basic fallback prompt
        """
        return """Eres un experto en Marketing Digital y análisis de datos de campañas de Facebook Ads. 
        Ayuda al usuario a analizar el rendimiento de sus campañas publicitarias y proporciona insights valiosos."""
    
    def _create_agent(self):
        """
        Create the LangChain agent with tools and prompt.
        
        Returns:
            Configured LangChain agent
        """
        # Get system prompt from configured source
        system_prompt = self._get_system_prompt()
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return agent
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        Create the agent executor with memory and error handling.
        
        Returns:
            Configured AgentExecutor
        """
        return AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,  # Enable detailed logging
            handle_parsing_errors=True,  # Handle tool parsing errors gracefully
            max_iterations=AGENT_MAX_ITERATIONS,  # Configurable limit to prevent infinite loops
            early_stopping_method="generate"  # Stop early if agent generates final answer
        )
    
    def process_message(self, message: str) -> str:
        """
        Process a user message and return agent response.
        
        Args:
            message: User's input message
        
        Returns:
            Agent's response
        """
        try:
            logger.info(f"Processing message for user {self.user_id}: {message[:100]}...")
            
            # Execute agent with user input
            response = self.agent_executor.invoke({
                "input": message
            })
            
            # Extract response text
            response_text = response.get("output", "Lo siento, no pude procesar tu solicitud.")
            
            logger.info(f"Generated response for user {self.user_id}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Lo siento, ocurrió un error al procesar tu solicitud: {str(e)}"
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about the current session.
        
        Returns:
            Dictionary with session information
        """
        return self.memory.get_session_info()
    
    def clear_session(self) -> None:
        """
        Clear the current conversation session.
        """
        self.memory.clear_session()
        logger.info(f"Cleared session for user {self.user_id}")
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.
        
        Returns:
            Conversation summary
        """
        return self.memory.get_conversation_summary()

# === Utility Functions ===

def generate_session_id(user_id: str) -> str:
    """
    Generate a readable session ID using timestamp and user_id.
    
    Args:
        user_id: User identifier (email)
    
    Returns:
        Formatted session ID: timestamp_userid
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean user_id for filename compatibility
    clean_user_id = user_id.replace("@", "_at_").replace(".", "_")
    return f"{timestamp}_{clean_user_id}"
