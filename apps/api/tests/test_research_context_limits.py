from types import SimpleNamespace

from app.agents import research_agent


def test_research_agent_bounds_untrusted_search_context_and_history(monkeypatch):
    captured = []

    class Search:
        def invoke(self, query):
            assert query == {"query": "Explain preventive care"}
            return {"results": [{
                "url": "https://example.org/prevention",
                "title": "Prevention",
                "content": "x" * 100_000,
            }]}

    class LLM:
        def invoke(self, messages):
            captured.extend(messages)
            return SimpleNamespace(content="General preventive care overview")

    monkeypatch.setattr(research_agent, "get_web_search", lambda: Search())
    monkeypatch.setattr(research_agent, "get_llm", lambda: LLM())

    history = [{"role": "user", "content": "y" * 50_000} for _ in range(20)]
    result = research_agent.invoke_research_agent("Explain preventive care", history)

    assert result["response"] == "General preventive care overview"
    assert result["sources"] == [{"title": "Prevention", "url": "https://example.org/prevention"}]
    assert len(captured) == 12  # System + last ten messages + new user request
    assert all(len(str(message.content)) <= 2_000 for message in captured[1:-1])
    assert len(str(captured[-1].content)) <= research_agent.MAX_SEARCH_CONTEXT_CHARS + 100
    assert len(str(captured[-1].content)) > 100
