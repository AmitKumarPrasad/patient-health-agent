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


def test_research_context_ignores_unapproved_tool_fields():
    from app.agents.research_agent import _search_context

    payload = {"results": [
        {
            "url": "https://example.org/guide",
            "title": "Healthcare guide",
            "content": "Public educational overview",
            "internal_token": "DO_NOT_INCLUDE_SECRET",
            "tool_metadata": {"prompt": "DO_NOT_INCLUDE_TOOL_INSTRUCTIONS"},
        },
        {"url": "http://127.0.0.1/admin", "title": "Private", "content": "DO_NOT_INCLUDE_PRIVATE"},
        {"url": "javascript:alert(1)", "content": "DO_NOT_INCLUDE_UNSAFE"},
    ]}
    context = _search_context(payload)
    assert "Healthcare guide" in context
    assert "Public educational overview" in context
    assert "DO_NOT_INCLUDE_SECRET" not in context
    assert "DO_NOT_INCLUDE_TOOL_INSTRUCTIONS" not in context
    assert "DO_NOT_INCLUDE_PRIVATE" not in context
    assert "DO_NOT_INCLUDE_UNSAFE" not in context


def test_research_context_caps_excerpts_and_rejects_malformed_tool_results():
    from app.agents.research_agent import _search_context, MAX_RESULT_EXCERPT_CHARS

    context = _search_context({"results": [
        {"url": "https://example.org/article", "content": "x" * 100_000},
    ]})
    assert context.count("x") == MAX_RESULT_EXCERPT_CHARS
    assert _search_context({"results": "not-a-list"}) == "[]"
    assert _search_context(None) == "[]"
