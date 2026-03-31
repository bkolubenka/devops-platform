import json

import httpx


def _create_service(client, name="backend"):
    return client.post("/api/services", json={
        "name": name,
        "service_type": "api",
        "description": "A test backend service",
        "environment": "dev",
        "status": "running",
    }).json()


def test_analyze_incident_by_service_id(client):
    svc = _create_service(client)
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Backend returns 500 errors, database connection refused",
        "affected_service_id": svc["id"],
        "severity": "critical",
        "symptoms": "Connection refused to postgres",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "incident_class" in data
    assert "priority" in data
    assert "suspected_causes" in data
    assert "service_context" in data
    assert data["service_context"]["name"] == "backend"


def test_analyze_incident_by_service_name(client):
    _create_service(client, "nginx")
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "502 bad gateway when accessing the frontend",
        "affected_service_name": "nginx",
        "severity": "high",
        "symptoms": "Nginx returning bad gateway errors",
    })
    assert resp.status_code == 200
    assert resp.json()["service_context"]["name"] == "nginx"


def test_analyze_missing_service(client):
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Something is broken in the system",
        "affected_service_id": 999,
        "severity": "medium",
        "symptoms": "Unknown errors happening",
    })
    assert resp.status_code == 404


def test_analyze_requires_service_reference(client):
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Something is broken",
        "severity": "medium",
        "symptoms": "Unknown errors",
    })
    assert resp.status_code == 422


def test_classification_database(client):
    svc = _create_service(client, "db")
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Database connection refused",
        "affected_service_id": svc["id"],
        "severity": "critical",
        "symptoms": "PostgreSQL not accepting connections",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "database_connectivity"


def test_classification_deployment(client):
    svc = _create_service(client)
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Service broken after deploy",
        "affected_service_id": svc["id"],
        "severity": "high",
        "symptoms": "Not working since new version",
        "recent_changes": "Deployed new release yesterday",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "deployment_regression"


def test_generate_text(client):
    resp = client.post("/api/ai/generate-text", json={
        "prompt": "Tell me about devops",
    })
    assert resp.status_code == 200
    assert "generated_text" in resp.json()


def test_generate_text_incident(client):
    resp = client.post("/api/ai/generate-text", json={
        "prompt": "How do I handle a service incident?",
    })
    assert resp.status_code == 200
    assert "incident assistant" in resp.json()["generated_text"]


def test_get_models(client):
    resp = client.get("/api/ai/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert len(data["models"]) == 2


def test_ollama_enrichment_merges_guidance(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": json.dumps(
                    {
                        "suspected_causes": ["Connection pool exhausted under load"],
                        "recommended_checks": ["Inspect DB connection pool saturation"],
                        "suggested_runbook": ["Temporarily reduce worker concurrency"],
                        "confidence": "high",
                    }
                )
            }

    def fake_post(*args, **kwargs):
        return DummyResponse()

    monkeypatch.setattr(main_module.httpx, "post", fake_post)

    svc = _create_service(client, "backend")
    resp = client.post(
        "/api/ai/incidents/analyze",
        json={
            "summary": "Backend returns 500 errors after traffic spike",
            "affected_service_id": svc["id"],
            "severity": "high",
            "symptoms": "Intermittent failures and timeouts",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["suspected_causes"][0] == "Connection pool exhausted under load"
    assert data["recommended_checks"][0] == "Inspect DB connection pool saturation"
    assert data["suggested_runbook"][0] == "Temporarily reduce worker concurrency"
    assert data["confidence"] == "high"


def test_ollama_failure_falls_back_to_rule_based(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    def failing_post(*args, **kwargs):
        raise httpx.ConnectError("ollama offline")

    monkeypatch.setattr(main_module.httpx, "post", failing_post)

    svc = _create_service(client, "db")
    resp = client.post(
        "/api/ai/incidents/analyze",
        json={
            "summary": "Database connection refused",
            "affected_service_id": svc["id"],
            "severity": "critical",
            "symptoms": "PostgreSQL not accepting connections",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_class"] == "database_connectivity"
    assert any("PostgreSQL" in item for item in data["suspected_causes"])
