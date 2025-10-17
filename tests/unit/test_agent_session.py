import pytest
from unittest.mock import MagicMock

from src.agent.agent_executor import DigitalMarketingAgent


class DummyLLM:
    """Mock LLM compatible with LangChain's create_openai_tools_agent."""
    def __init__(self):
        self.model_name = "dummy"
        self.temperature = 0.7
        self.max_tokens = 1000
        # Attributes sometimes inspected by code/tests
        self._model_type = "chat"
        self._llm_type = "azure_openai"

    def bind(self, **kwargs):
        """Mimic LangChain LLM .bind() by returning self regardless of kwargs."""
        return self

    def invoke(self, *args, **kwargs):
        return "Mock response"

    def __call__(self, *args, **kwargs):
        return self.invoke(*args, **kwargs)

    def get_ls_params(self):
        return {}


def _fake_create_llm(self):
    return DummyLLM()


def _fake_create_memory(user_id, session_id, llm):
    class _M:
        def __init__(self, sid):
            self.session_id = sid
            # Mock the memory interface that DigitalMarketingAgent expects
            self.chat_memory = MagicMock()
            self.chat_memory.messages = []

        def __getattr__(self, name):
            # Return mock for any other attribute access
            return MagicMock()

    return _M(session_id)


@pytest.mark.unit
def test_persistent_session_id_monkeypatch(monkeypatch):
    # Mock the entire memory creation to avoid Pydantic validation issues
    monkeypatch.setattr(
        DigitalMarketingAgent,
        "_create_llm",
        _fake_create_llm,
        raising=True,
    )

    import src.agent.memory as memory_mod

    monkeypatch.setattr(
        memory_mod,
        "create_memory",
        _fake_create_memory,
        raising=True,
    )

    # Also mock ConversationSummaryBufferMemory to avoid Pydantic validation
    from unittest.mock import patch
    with patch('src.agent.memory.ConversationSummaryBufferMemory'):
        agent1 = DigitalMarketingAgent(user_id=1)
        agent2 = DigitalMarketingAgent(user_id=1)
        agent3 = DigitalMarketingAgent(user_id=2)

        assert agent1.session_id == agent2.session_id == "persistent_1"
        assert agent3.session_id == "persistent_2"
