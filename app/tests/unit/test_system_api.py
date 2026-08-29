###############################################################################
def test_health_reports_fairs_metadata(monkeypatch):
    monkeypatch.setenv("KERAS_BACKEND", "torch")
    from server.api.system import health
    from server.contracts.system import HealthResponse

    monkeypatch.setattr("server.api.system.get_application_version", lambda: "3.1.0")
    response = health()
    assert isinstance(response, HealthResponse)
    assert response.status == "ok"
    assert response.application == "FAIRS"
    assert response.version == "3.1.0"
