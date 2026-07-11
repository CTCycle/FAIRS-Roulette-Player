def test_health_reports_fairs_metadata(monkeypatch):
    monkeypatch.setenv("KERAS_BACKEND", "torch")
    monkeypatch.delenv("FAIRS_TAURI_MODE", raising=False)
    from server.api.system import health

    response = health()
    assert response["application"] == "FAIRS"
    assert response["mode"] == "development"
