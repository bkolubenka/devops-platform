import json

import httpx


def _create_service(client, name="backend", service_type="api", **kwargs):
    payload = {
        "name": name,
        "service_type": service_type,
        "description": "A test backend service",
        "environment": "dev",
        "status": "running",
    }
    payload.update(kwargs)
    return client.post("/api/services", json=payload).json()


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


def test_classification_reverse_proxy(client):
    svc = _create_service(client, "nginx", service_type="reverse-proxy")
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "502 bad gateway on all requests",
        "affected_service_id": svc["id"],
        "severity": "high",
        "symptoms": "Nginx returning bad gateway errors to all clients",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "reverse_proxy_routing"


def test_classification_high_latency(client):
    svc = _create_service(client)
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Requests are very slow and timing out",
        "affected_service_id": svc["id"],
        "severity": "medium",
        "symptoms": "High latency observed, performance degraded",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "high_latency"


def test_classification_service_unavailable(client):
    svc = _create_service(client)
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Service is completely down and unavailable",
        "affected_service_id": svc["id"],
        "severity": "critical",
        "symptoms": "Service stopped responding, connection refused",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "service_unavailable"


def test_classification_unknown(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setattr(main_module, "check_http_target", lambda url: (True, "http 200"))

    svc = _create_service(
        client,
        name="healthy-api",
        health_endpoint="http://localhost:9999/health",
    )
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Something odd is happening",
        "affected_service_id": svc["id"],
        "severity": "low",
        "symptoms": "Occasional unexpected output",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "unknown"


def test_analyze_by_incident_id(client):
    svc = _create_service(client)
    inc = client.post("/api/incidents", json={
        "title": "Existing incident",
        "affected_service_id": svc["id"],
        "severity": "high",
        "summary": "Database connection refused on startup",
        "symptoms": "Backend returns 500 errors on DB calls",
        "status": "open",
    }).json()
    resp = client.post("/api/ai/incidents/analyze", json={
        "incident_id": inc["id"],
        "summary": "Database connection refused on startup",
        "severity": "high",
        "symptoms": "Backend returns 500 errors on DB calls",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "incident_class" in data
    assert data["service_context"]["name"] == svc["name"]


def test_analyze_by_incident_id_not_found(client):
    svc = _create_service(client)
    resp = client.post("/api/ai/incidents/analyze", json={
        "incident_id": 9999,
        "summary": "Something broken",
        "severity": "medium",
        "symptoms": "Unknown errors happening",
    })
    assert resp.status_code == 404


def test_analysis_saved_to_matching_incident(client):
    svc = _create_service(client)
    inc_resp = client.post("/api/incidents", json={
        "title": "Incident for analysis save",
        "affected_service_id": svc["id"],
        "severity": "medium",
        "summary": "Service connection refused consistently",
        "symptoms": "Service returning connection errors",
        "status": "open",
    })
    assert inc_resp.status_code == 201
    inc_id = inc_resp.json()["id"]

    client.post("/api/ai/incidents/analyze", json={
        "summary": "Service connection refused consistently",
        "affected_service_id": svc["id"],
        "severity": "medium",
        "symptoms": "Service returning connection errors",
    })

    inc_detail = client.get(f"/api/incidents/{inc_id}").json()
    assert inc_detail["analysis"] is not None
    assert "incident_class" in inc_detail["analysis"]


def test_service_context_guidance_with_health_endpoint_and_owner(client):
    svc = _create_service(
        client,
        name="backend",
        url="http://localhost:8000",
        health_endpoint="http://localhost:8000/health",
        owner="platform-team",
    )
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Backend returns 500 errors",
        "affected_service_id": svc["id"],
        "severity": "high",
        "symptoms": "All endpoints failing",
    })
    assert resp.status_code == 200
    data = resp.json()
    all_checks = " ".join(data["recommended_checks"] + data["suggested_runbook"])
    assert "http://localhost:8000/health" in all_checks
    assert "http://localhost:8000" in all_checks
    assert "platform-team" in all_checks


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


def test_generate_text_portfolio(client):
    resp = client.post("/api/ai/generate-text", json={
        "prompt": "Tell me about the portfolio",
    })
    assert resp.status_code == 200
    assert "portfolio" in resp.json()["generated_text"].lower()


def test_generate_text_unknown_prompt(client):
    resp = client.post("/api/ai/generate-text", json={
        "prompt": "xyzzy frobulate nothing special",
    })
    assert resp.status_code == 200
    assert "xyzzy frobulate nothing special" in resp.json()["generated_text"]


def test_generate_text_max_length_truncation(client):
    resp = client.post("/api/ai/generate-text", json={
        "prompt": "Tell me about devops",
        "max_length": 10,
    })
    assert resp.status_code == 200
    assert len(resp.json()["generated_text"]) <= 10


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


def test_ollama_non_json_response_falls_back(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    class NonJsonResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "Sorry, I cannot help with that right now."}

    monkeypatch.setattr(main_module.httpx, "post", lambda *a, **kw: NonJsonResponse())

    svc = _create_service(client, "backend")
    resp = client.post(
        "/api/ai/incidents/analyze",
        json={
            "summary": "Backend is failing badly",
            "affected_service_id": svc["id"],
            "severity": "high",
            "symptoms": "All requests returning errors",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "incident_class" in data


def test_ollama_empty_lists_falls_back(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    class EmptyListResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": json.dumps({
                    "suspected_causes": [],
                    "recommended_checks": [],
                    "suggested_runbook": [],
                    "confidence": "low",
                })
            }

    monkeypatch.setattr(main_module.httpx, "post", lambda *a, **kw: EmptyListResponse())

    svc = _create_service(client, "backend")
    resp = client.post(
        "/api/ai/incidents/analyze",
        json={
            "summary": "Backend failing with unknown error",
            "affected_service_id": svc["id"],
            "severity": "medium",
            "symptoms": "Intermittent failures observed",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["suspected_causes"]) > 0


def test_ollama_non_string_response_field_falls_back(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    class NullResponseField:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": None}

    monkeypatch.setattr(main_module.httpx, "post", lambda *a, **kw: NullResponseField())

    svc = _create_service(client, "backend")
    resp = client.post(
        "/api/ai/incidents/analyze",
        json={
            "summary": "Backend returning errors",
            "affected_service_id": svc["id"],
            "severity": "high",
            "symptoms": "All endpoints timing out",
        },
    )
    assert resp.status_code == 200


def test_ollama_with_historical_incidents(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    call_count = {"n": 0}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": json.dumps({
                    "suspected_causes": ["Recurring DB issue"],
                    "recommended_checks": ["Check DB logs again"],
                    "suggested_runbook": ["Restart DB container"],
                    "confidence": "medium",
                })
            }

    monkeypatch.setattr(main_module.httpx, "post", lambda *a, **kw: DummyResponse())

    svc = _create_service(client, "db")

    # Create a prior incident with analysis so history is non-empty
    client.post("/api/incidents", json={
        "title": "Prior DB incident",
        "affected_service_id": svc["id"],
        "severity": "critical",
        "summary": "Prior database connection failure",
        "symptoms": "PostgreSQL not accepting connections",
        "status": "resolved",
    })

    resp = client.post(
        "/api/ai/incidents/analyze",
        json={
            "summary": "Database connection refused again",
            "affected_service_id": svc["id"],
            "severity": "critical",
            "symptoms": "PostgreSQL still not accepting connections",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["suspected_causes"][0] == "Recurring DB issue"
