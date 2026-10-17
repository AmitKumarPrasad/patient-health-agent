from app.agents.research_agent import _source_metadata, is_safe_source_url


def test_source_urls_allow_only_normal_web_links():
    assert is_safe_source_url("https://example.org/article")
    assert is_safe_source_url("http://example.org/path?x=1")
    for value in (
        "javascript:alert(1)",
        "data:text/html,hello",
        "file:///etc/passwd",
        "//example.org",
        "https://user:password@example.org",
        "https://example.org/path\\nattack",
        "https://example.org:bad/path",
        "https://example.org/path\nattack",
        "https://",
        "https://example.org/" + "a" * 1000,
    ):
        assert not is_safe_source_url(value)


def test_source_metadata_deduplicates_and_filters_unsafe_urls():
    results = {"results": [
        {"url": "javascript:alert(1)", "title": "Unsafe"},
        {"url": "https://example.org/a", "title": "Valid"},
        {"url": "https://example.org/a", "title": "Duplicate"},
        {"url": "data:text/html,boom", "title": "Unsafe"},
        {"url": "http://example.org/b", "title": "Another"},
    ]}
    assert _source_metadata(results) == [
        {"title": "Valid", "url": "https://example.org/a"},
        {"title": "Another", "url": "http://example.org/b"},
    ]
