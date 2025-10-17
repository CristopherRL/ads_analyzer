import pytest

from src.agent.agent_executor import DigitalMarketingAgent


class DummyLLM:
    pass


def _fake_create_llm(self):
    return DummyLLM()


def _fake_create_memory(user_id, session_id, llm):
    class _M:
        def __init__(self, sid):
            self.session_id = sid

        def __getattr__(self, name):
            # minimal interface to satisfy accesses during construction if any
            if name == "chat_memory":
                class _CM:
                    messages = []
                return _CM()
            raise AttributeError

    return _M(session_id)


@pytest.mark.unit
def test_persistent_session_id_monkeypatch(monkeypatch):
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

    agent1 = DigitalMarketingAgent(user_id=1)
    agent2 = DigitalMarketingAgent(user_id=1)
    agent3 = DigitalMarketingAgent(user_id=2)

    assert agent1.session_id == agent2.session_id == "persistent_1"
    assert agent3.session_id == "persistent_2"
