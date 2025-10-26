import pytest
from unittest.mock import MagicMock, patch
from src.agent.memory import DatabaseConversationMemory, create_memory

@pytest.fixture
def mock_db_session():
    """Fixture to create a mock database session."""
    db_session = MagicMock()
    # Mock the query method to return a query object
    db_session.query.return_value = MagicMock()
    return db_session

@pytest.fixture
def mock_get_db(mock_db_session):
    """Fixture to patch get_db to return the mock_db_session repeatedly."""
    with patch('src.agent.memory.get_db') as mock_get_db:
        mock_get_db.side_effect = lambda: iter([mock_db_session])
        yield mock_get_db

@pytest.fixture
def mock_llm():
    """Fixture to create a mock LLM."""
    return MagicMock()

def test_create_memory(mock_get_db, mock_llm):
    """Test the create_memory factory function."""
    with patch('src.agent.memory.ConversationSummaryBufferMemory'):
        memory = create_memory(user_id=1, session_id="test_session", llm=mock_llm)
        assert isinstance(memory, DatabaseConversationMemory)
        assert memory.user_id == 1
        assert memory.session_id == "test_session"

def test_database_conversation_memory_init(mock_get_db, mock_llm):
    """Test the initialization of DatabaseConversationMemory."""
    with patch('src.agent.memory.ConversationSummaryBufferMemory'):
        with patch.object(DatabaseConversationMemory, '_load_conversation_history') as mock_load_history:
            with patch.object(DatabaseConversationMemory, '_load_long_term_memory') as mock_load_long_term_memory:
                memory = DatabaseConversationMemory(user_id=1, session_id="test_session", llm=mock_llm)
                assert memory.user_id == 1
                assert memory.session_id == "test_session"
                mock_load_history.assert_called_once()
                mock_load_long_term_memory.assert_called_once()

def test_load_conversation_history(mock_db_session, mock_get_db, mock_llm):
    """Test loading conversation history from the database."""
    mock_conversation = MagicMock()
    mock_conversation.user_prompt = "Hello"
    mock_conversation.llm_response = "Hi"
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_conversation]

    with patch('src.agent.memory.ConversationSummaryBufferMemory'):
        memory = DatabaseConversationMemory(user_id=1, session_id="test_session", llm=mock_llm)
        # Manually trigger loading for assertion since __init__ is complex
        memory._memory.chat_memory.messages = []
        memory._load_conversation_history()
        assert len(memory._memory.chat_memory.messages) > 0
        assert "Hello" in [msg.content for msg in memory._memory.chat_memory.messages]

def test_save_conversation_pair(mock_db_session, mock_get_db, mock_llm):
    """Test saving a conversation pair to the database."""
    with patch('src.agent.memory.ConversationSummaryBufferMemory'):
        with patch('src.agent.memory.CostCalculator') as mock_cost_calculator:
            mock_cost_calculator.estimate_tokens_from_text.return_value = 10
            mock_cost_calculator.calculate_cost.return_value = 0.001
            memory = DatabaseConversationMemory(user_id=1, session_id="test_session", llm=mock_llm)
            memory._save_conversation_pair("Hello", "Hi", "Full prompt", {"model_name": "test_model"})
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()

def test_clear_session(mock_db_session, mock_get_db, mock_llm):
    """Test clearing the session from memory and database."""
    with patch('src.agent.memory.ConversationSummaryBufferMemory'):
        memory = DatabaseConversationMemory(user_id=1, session_id="test_session", llm=mock_llm)
        memory.clear_session()
        mock_db_session.query.return_value.filter.return_value.delete.assert_called_once()
        mock_db_session.commit.assert_called_once()
        memory._memory.clear.assert_called_once()
