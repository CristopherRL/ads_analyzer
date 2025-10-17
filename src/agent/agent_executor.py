# === File: src/agent/agent_executor.py ===

from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI
from sqlalchemy import and_
from datetime import datetime, timedelta

from src.agent.memory import DatabaseConversationMemory, create_memory
from src.tools.facebook_tools import list_available_clients_tool, facebook_ads_analysis_tool
from src.utils.cost_calculator import CostCalculator
from src.database import get_db
from src.models import AnalysisResult, FacebookAccount
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
    
    def __init__(self, user_id: int, session_id: Optional[str] = None):
        """
        Initialize the Digital Marketing Agent.
        
        Args:
            user_id: User ID (foreign key to users table)
            session_id: Optional session identifier for conversation continuity
        """
        self.user_id = user_id
        self.user_name = self._get_user_name(user_id)
        self.session_id = self._get_or_create_session(user_id, session_id)
        
        # Initialize components
        self.llm = self._create_llm()
        self.memory = create_memory(user_id, self.session_id, self.llm)
        self.tools = self._get_tools()
        self.agent = self._create_agent()
        self.agent_executor = self._create_agent_executor()
        
        logger.info(f"Initialized Digital Marketing Agent for user {user_id} ({self.user_name}) with session {self.session_id}")
    
    def _get_user_name(self, user_id: int) -> str:
        """
        Get user name from database.
        
        Args:
            user_id: User ID to look up
            
        Returns:
            User name or 'Usuario' as fallback
        """
        try:
            from src.database import get_db
            from src.models import User
            
            db_gen = get_db()
            db = next(db_gen)
            
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.name:
                return user.name
            else:
                return "Usuario"
                
        except Exception as e:
            logger.error(f"Error getting user name: {e}")
            return "Usuario"
        finally:
            if 'db' in locals():
                db.close()
    
    def _get_or_create_session(self, user_id: int, provided_session_id: Optional[str] = None) -> str:
        """
        Get or create a persistent session ID for the user.
        
        Args:
            user_id: User ID
            provided_session_id: Optional session ID (ignored for persistent sessions)
            
        Returns:
            Persistent session ID
        """
        # Session ID persistente: siempre el mismo para el usuario
        persistent_session_id = f"persistent_{user_id}"
        logger.info(f"Using persistent session: {persistent_session_id}")
        return persistent_session_id
    
    def _is_session_valid(self, session_id: str, timeout_minutes: int = 30) -> bool:
        """
        Always valid for persistent session IDs.
        
        Args:
            session_id: Session ID to validate
            timeout_minutes: Session timeout in minutes (ignored for persistent sessions)
            
        Returns:
            Always True for persistent sessions
        """
        # Session ID persistente: siempre válida
        return True
    
    def _create_llm(self) -> AzureChatOpenAI:
        """
        Create and configure the Azure OpenAI LLM.
        
        Returns:
            Configured AzureChatOpenAI instance
        
        """
        return AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,  # Use deployment name
            api_key=AZURE_OPENAI_API_KEY,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version=AZURE_API_VERSION,
            temperature=AGENT_TEMPERATURE,  # Configurable temperature for balanced creativity
            max_tokens=AGENT_MAX_TOKENS,
            model=AZURE_OPENAI_DEPLOYMENT_NAME  # Required for token counting
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
            System prompt string with user personalization
        """
        if SYSTEM_PROMPT_SOURCE == 'database':
            base_prompt = self._load_prompt_from_database()
        else:
            base_prompt = self._load_prompt_from_file()
        
        # Personalize prompt with user name
        personalized_prompt = self._personalize_prompt(base_prompt)
        return personalized_prompt
    
    def _personalize_prompt(self, base_prompt: str) -> str:
        """
        Personalize system prompt with user information.
        
        Args:
            base_prompt: Base system prompt
            
        Returns:
            Personalized prompt with user name
        """
        # Add user personalization at the beginning
        personalization = f"El usuario con el que estás hablando se llama {self.user_name}. "
        
        # Combine personalization with base prompt
        return base_prompt + personalization
    
    def _load_prompt_from_file(self) -> str:
        """
        Load system prompt from default file.
        
        Returns:
            System prompt string
        """
        try:
            with open(DEFAULT_PROMPT_FILE, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
            
            # Validate prompt content
            if not prompt or len(prompt.strip()) == 0:
                logger.error("Prompt file is empty")
                return self._get_fallback_prompt()
            
            logger.info(f"Loaded system prompt from file: {DEFAULT_PROMPT_FILE}")
            logger.info(f"Prompt length: {len(prompt)} characters")
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
        return """You are a Digital Marketing expert and Facebook Ads campaign data analyst. 
        Help the user analyze the performance of their advertising campaigns and provide valuable insights."""
    
    def _create_agent(self):
        """
        Create the LangChain agent with tools and prompt.
        
        Returns:
            Configured LangChain agent
        """
        try:
            # Get system prompt from configured source
            logger.info("Getting system prompt...")
            system_prompt = self._get_system_prompt()
            logger.info(f"System prompt loaded, length: {len(system_prompt)}")
            
            # Create prompt template
            logger.info("Creating prompt template...")
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            logger.info("Prompt template created successfully")
            
            # Create agent
            logger.info("Creating OpenAI tools agent...")
            agent = create_openai_tools_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            logger.info("Agent created successfully")
            
            return agent
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
    
    def _create_agent_executor(self) -> AgentExecutor:
        """
        Create the agent executor with memory and error handling.
        
        Returns:
            Configured AgentExecutor
        """
        return AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,  # Enable detailed logging
            handle_parsing_errors=True,  # Handle tool parsing errors gracefully
            max_iterations=AGENT_MAX_ITERATIONS,  # Configurable limit to prevent infinite loops
            early_stopping_method="generate",  # Stop early if agent generates final answer
            return_intermediate_steps=True  # Include intermediate steps in response
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
            # Validate input message
            if not message or not isinstance(message, str):
                logger.error(f"Invalid message received: {message}")
                return "Sorry, this message is not valid."
            
            logger.info(f"Processing message for user {self.user_id}: {message[:100]}...")
            
            # Get chat history from memory
            chat_history = self.memory.chat_memory.messages
            logger.info(f"Chat history length: {len(chat_history)}")
            
            # Execute agent with user input and chat history
            logger.info("Invoking agent executor...")
            response = self.agent_executor.invoke({
                "input": message,
                "chat_history": chat_history
            })
            logger.info(f"Agent response received: {type(response)}")
            
            # Extract response text
            response_text = response.get("output", "Sorry, I couldn't process your request.")
            logger.info(f"Response text extracted: {response_text[:100]}...")
            
            # Extract tool/function used from response (try multiple methods)
            tool_used = self._extract_tool_used(response)
            if not tool_used:
                # Try to extract from intermediate steps if available
                tool_used = self._extract_tool_from_intermediate_steps(response)
            logger.info(f"Tool used: {tool_used}")
            
            # Extract tool parameters (like facebook_account_id) from response
            tool_params = self._extract_tool_parameters(response)
            logger.info(f"Tool parameters: {tool_params}")
            
            # Prepare LLM parameters for tracking
            llm_params = CostCalculator.get_llm_params_dict(
                model_name=AZURE_OPENAI_DEPLOYMENT_NAME,
                temperature=AGENT_TEMPERATURE,
                max_tokens=AGENT_MAX_TOKENS
            )
            
            # Get full prompt for tracking (system prompt + chat history + user message)
            full_prompt = self._get_full_prompt_for_tracking(message, chat_history)
            
            # Save conversation to memory with full tracking
            self.memory.save_context(
                {"input": message},
                {"output": response_text},
                full_prompt_sent=full_prompt,
                llm_params=llm_params
            )
            
            # Check if a tool was used and save analysis result
            if tool_used:
                self._save_analysis_result(response_text, tool_used, message, tool_params)
            
            logger.info(f"Generated response for user {self.user_id}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"Sorry, an error occurred while processing your request: {str(e)}"
    
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
    
    def _get_full_prompt_for_tracking(self, user_message: str, chat_history: List) -> str:
        """
        Get the full prompt that would be sent to the LLM for tracking purposes.
        
        Args:
            user_message: Current user message
            chat_history: List of previous messages
            
        Returns:
            Full prompt string for tracking
        """
        try:
            # Get system prompt
            system_prompt = self._get_system_prompt()
            
            # Build full prompt
            full_prompt_parts = [f"System: {system_prompt}"]
            
            # Add chat history
            for msg in chat_history:
                if hasattr(msg, 'content'):
                    if hasattr(msg, 'type'):
                        if msg.type == 'human':
                            full_prompt_parts.append(f"Human: {msg.content}")
                        elif msg.type == 'ai':
                            full_prompt_parts.append(f"AI: {msg.content}")
                    else:
                        # Fallback for different message types
                        full_prompt_parts.append(f"Message: {msg.content}")
            
            # Add current user message
            full_prompt_parts.append(f"Human: {user_message}")
            
            return "\n\n".join(full_prompt_parts)
            
        except Exception as e:
            logger.error(f"Error building full prompt for tracking: {e}")
            return f"System: {self._get_system_prompt()}\n\nHuman: {user_message}"
    
    def _extract_tool_used(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract the tool/function name used by the agent from the response.
        
        Args:
            response: The agent's response dictionary
            
        Returns:
            Tool name if a tool was used, None otherwise
        """
        try:
            # Check if the response contains intermediate steps (tool calls)
            if 'intermediate_steps' in response:
                intermediate_steps = response['intermediate_steps']
                if intermediate_steps:
                    # Get the last tool used
                    last_step = intermediate_steps[-1]
                    if len(last_step) >= 2:
                        action = last_step[0]
                        if hasattr(action, 'tool'):
                            tool_name = action.tool
                            logger.info(f"Tool used: {tool_name}")
                            return tool_name
                        elif hasattr(action, 'tool_name'):
                            tool_name = action.tool_name
                            logger.info(f"Tool used: {tool_name}")
                            return tool_name
            
            # Alternative: check if response contains tool information in other formats
            if isinstance(response, dict):
                # Look for tool information in various possible locations
                for key in ['tool', 'tool_name', 'function_name', 'action']:
                    if key in response and response[key]:
                        logger.info(f"Tool found in {key}: {response[key]}")
                        return str(response[key])
            
            logger.info("No tool was used in this response")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting tool used: {e}")
            return None
    
    def _extract_tool_from_intermediate_steps(self, response: Dict[str, Any]) -> Optional[str]:
        """
        Extract tool name from intermediate steps in the response.
        
        Args:
            response: The agent's response dictionary
            
        Returns:
            Tool name if found in intermediate steps, None otherwise
        """
        try:
            # Check if intermediate_steps exists and has content
            if 'intermediate_steps' in response and response['intermediate_steps']:
                intermediate_steps = response['intermediate_steps']
                logger.info(f"Found {len(intermediate_steps)} intermediate steps")
                
                # Get the last tool used (most recent)
                for step in reversed(intermediate_steps):
                    if len(step) >= 2:
                        action = step[0]
                        # Check various possible attributes for tool name
                        if hasattr(action, 'tool') and action.tool:
                            logger.info(f"Found tool in action.tool: {action.tool}")
                            return action.tool
                        elif hasattr(action, 'tool_name') and action.tool_name:
                            logger.info(f"Found tool in action.tool_name: {action.tool_name}")
                            return action.tool_name
                        elif hasattr(action, 'action') and action.action:
                            logger.info(f"Found tool in action.action: {action.action}")
                            return action.action
                
                logger.info("No tool found in intermediate steps")
                return None
            else:
                logger.info("No intermediate steps found in response")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting tool from intermediate steps: {e}")
            return None
    
    def _extract_tool_parameters(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract tool parameters from the response.
        
        Args:
            response: The agent's response dictionary
            
        Returns:
            Dictionary with tool parameters (e.g., {'ad_account_id': 'act_123456'})
        """
        try:
            # Check if intermediate_steps exists and has content
            if 'intermediate_steps' in response and response['intermediate_steps']:
                intermediate_steps = response['intermediate_steps']
                logger.info(f"Extracting parameters from {len(intermediate_steps)} intermediate steps")
                
                # Get parameters from the last tool used (most recent)
                for step in reversed(intermediate_steps):
                    if len(step) >= 2:
                        action = step[0]
                        # Check for tool_input parameter
                        if hasattr(action, 'tool_input') and action.tool_input:
                            tool_input = action.tool_input
                            logger.info(f"Found tool parameters: {tool_input}")
                            return tool_input
                
                logger.info("No tool parameters found in intermediate steps")
                return {}
            else:
                logger.info("No intermediate steps found for parameter extraction")
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting tool parameters: {e}")
            return {}
    
    def _save_analysis_result(self, response_text: str, tool_used: str, user_message: str, tool_params: Dict[str, Any] = None) -> None:
        """
        Save analysis result to the database.
        
        Args:
            response_text: The complete analysis text
            tool_used: Name of the tool/function used by the agent
            user_message: Original user message that triggered the analysis
            tool_params: Parameters passed to the tool (e.g., {'ad_account_id': 'act_123456'})
        """
        try:
            db_gen = get_db()
            db = next(db_gen)
            
            # Extract Facebook account ID from tool parameters or fallback to text extraction
            facebook_account_id = None
            if tool_params and 'ad_account_id' in tool_params:
                # Get Facebook account ID from tool parameters
                ad_account_id = tool_params['ad_account_id']
                facebook_account = db.query(FacebookAccount).filter(
                    FacebookAccount.ad_account_id == ad_account_id
                ).first()
                if facebook_account:
                    facebook_account_id = facebook_account.id
                    logger.info(f"Found Facebook account ID: {facebook_account_id} for {ad_account_id}")
                else:
                    logger.warning(f"Facebook account not found in database for {ad_account_id}")
            else:
                # Fallback to text extraction method
                facebook_account_id = self._extract_facebook_account_id(user_message, response_text, db)
            
            # Prepare metadata including tool parameters
            metadata = {
                'tool_used': tool_used,
                'tool_parameters': tool_params or {},
                'user_message': user_message,
                'response_length': len(response_text),
                'saved_at': datetime.now().isoformat(),
                'session_id': self.memory.session_id
            }
            
            # Create analysis result record using tool name as analysis_type
            analysis_result = AnalysisResult(
                user_id=self.user_id,
                session_id=self.memory.session_id,
                analysis_type=tool_used,  # Use tool name as analysis type
                facebook_account_id=facebook_account_id,
                result_text=response_text,
                analysis_metadata=metadata
            )
            
            db.add(analysis_result)
            db.commit()
            
            logger.info(f"Saved analysis result using tool: {tool_used} for user {self.user_id} with facebook_account_id: {facebook_account_id}")
            
        except Exception as e:
            logger.error(f"Error saving analysis result: {e}")
            if 'db' in locals():
                db.rollback()
        finally:
            if 'db' in locals():
                db.close()
    
    def _extract_facebook_account_id(self, user_message: str, response_text: str, db) -> Optional[int]:
        """
        Try to extract Facebook account ID from message or response.
        
        Args:
            user_message: Original user message
            response_text: AI response text
            db: Database session
            
        Returns:
            Facebook account ID if found, None otherwise
        """
        try:
            import re
            
            # Look for account ID patterns in both messages
            text_to_search = f"{user_message} {response_text}"
            
            # Pattern for Facebook account IDs (act_ followed by numbers)
            account_pattern = r'act_(\d+)'
            matches = re.findall(account_pattern, text_to_search)
            
            if matches:
                # Get the first match and try to find it in the database
                account_id = f"act_{matches[0]}"
                facebook_account = db.query(FacebookAccount).filter(
                    FacebookAccount.ad_account_id == account_id
                ).first()
                
                if facebook_account:
                    logger.info(f"Found Facebook account ID: {facebook_account.id} for {account_id}")
                    return facebook_account.id
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting Facebook account ID: {e}")
            return None

# === Utility Functions ===

def generate_session_id(user_id: int) -> str:
    """
    Generate a readable session ID using timestamp and user_id.
    
    Args:
        user_id: User ID (foreign key to users table)
    
    Returns:
        Formatted session ID: timestamp_userid
    """
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean user_id for filename compatibility (convert to string first)
    clean_user_id = str(user_id).replace("@", "_at_").replace(".", "_")
    return f"{timestamp}_{clean_user_id}"
