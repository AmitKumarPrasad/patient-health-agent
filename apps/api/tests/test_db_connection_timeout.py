def test_database_engine_uses_configured_postgres_connect_timeout(monkeypatch) -> None:
    import app.db.session as db_session

    captured: dict[str, object] = {}

    def fake_create_engine(database_url: str, **kwargs):
        captured["database_url"] = database_url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(db_session, "create_engine", fake_create_engine)

    db_session.create_database_engine("postgresql+psycopg://example/db", 7)

    assert captured["database_url"] == "postgresql+psycopg://example/db"
    assert captured["connect_args"] == {"connect_timeout": 7}
    assert captured["pool_pre_ping"] is True
