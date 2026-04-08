"""Unit tests for pure utility functions in backend.main."""
import os


def test_normalize_advice_items_non_list():
    from backend.main import normalize_advice_items

    assert normalize_advice_items(None) == []
    assert normalize_advice_items("a string") == []
    assert normalize_advice_items(42) == []
    assert normalize_advice_items({}) == []


def test_normalize_advice_items_filters_empty_strings():
    from backend.main import normalize_advice_items

    assert normalize_advice_items(["", "   ", "good item"]) == ["good item"]


def test_normalize_advice_items_truncates_long_strings():
    from backend.main import normalize_advice_items

    long = "x" * 300
    result = normalize_advice_items([long])
    assert len(result[0]) == 240


def test_normalize_advice_items_respects_limit():
    from backend.main import normalize_advice_items

    items = ["item1", "item2", "item3", "item4", "item5", "item6", "item7"]
    result = normalize_advice_items(items)
    assert len(result) == 6


def test_normalize_advice_items_skips_non_strings():
    from backend.main import normalize_advice_items

    assert normalize_advice_items([1, None, "valid", True]) == ["valid"]


def test_merge_advice_deduplicates():
    from backend.main import merge_advice

    llm = ["Check DB logs", "Restart service"]
    rule = ["check db logs", "Validate config"]
    result = merge_advice(llm, rule)
    lower_result = [r.lower() for r in result]
    assert lower_result.count("check db logs") == 1


def test_merge_advice_respects_limit():
    from backend.main import merge_advice

    llm = ["a", "b", "c", "d", "e"]
    rule = ["f", "g", "h", "i"]
    result = merge_advice(llm, rule, limit=6)
    assert len(result) == 6


def test_merge_advice_llm_items_first():
    from backend.main import merge_advice

    llm = ["LLM item"]
    rule = ["Rule item"]
    result = merge_advice(llm, rule)
    assert result[0] == "LLM item"
    assert result[1] == "Rule item"


def test_extract_json_object_valid_json():
    from backend.main import extract_json_object

    result = extract_json_object('{"key": "value"}')
    assert result == {"key": "value"}


def test_extract_json_object_json_embedded_in_text():
    from backend.main import extract_json_object

    result = extract_json_object('Here is the result: {"key": "value"} done.')
    assert result == {"key": "value"}


def test_extract_json_object_no_braces():
    from backend.main import extract_json_object

    result = extract_json_object("no json here at all")
    assert result is None


def test_extract_json_object_invalid_json_in_braces():
    from backend.main import extract_json_object

    result = extract_json_object("{ this is not : valid json }")
    assert result is None


def test_extract_json_object_returns_none_for_json_array():
    from backend.main import extract_json_object

    result = extract_json_object("[1, 2, 3]")
    assert result is None


def test_env_flag_default_false():
    from backend.main import env_flag

    os.environ.pop("TEST_FLAG_XYZ", None)
    assert env_flag("TEST_FLAG_XYZ") is False


def test_env_flag_default_true():
    from backend.main import env_flag

    os.environ.pop("TEST_FLAG_XYZ", None)
    assert env_flag("TEST_FLAG_XYZ", default=True) is True


def test_env_flag_true_values():
    from backend.main import env_flag

    for val in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
        os.environ["TEST_FLAG_XYZ"] = val
        assert env_flag("TEST_FLAG_XYZ") is True

    os.environ.pop("TEST_FLAG_XYZ", None)


def test_env_flag_false_values():
    from backend.main import env_flag

    for val in ("0", "false", "False", "no", "off", ""):
        os.environ["TEST_FLAG_XYZ"] = val
        assert env_flag("TEST_FLAG_XYZ") is False

    os.environ.pop("TEST_FLAG_XYZ", None)


def test_get_ollama_timeout_seconds_default():
    from backend.main import get_ollama_timeout_seconds, OLLAMA_TIMEOUT_ENV

    os.environ.pop(OLLAMA_TIMEOUT_ENV, None)
    assert get_ollama_timeout_seconds() == 8.0


def test_get_ollama_timeout_seconds_custom():
    from backend.main import get_ollama_timeout_seconds, OLLAMA_TIMEOUT_ENV

    os.environ[OLLAMA_TIMEOUT_ENV] = "15"
    assert get_ollama_timeout_seconds() == 15.0
    os.environ.pop(OLLAMA_TIMEOUT_ENV, None)


def test_get_ollama_timeout_seconds_invalid_falls_back_to_8():
    from backend.main import get_ollama_timeout_seconds, OLLAMA_TIMEOUT_ENV

    os.environ[OLLAMA_TIMEOUT_ENV] = "not-a-number"
    assert get_ollama_timeout_seconds() == 8.0
    os.environ.pop(OLLAMA_TIMEOUT_ENV, None)


def test_get_ollama_timeout_seconds_clamps_min():
    from backend.main import get_ollama_timeout_seconds, OLLAMA_TIMEOUT_ENV

    os.environ[OLLAMA_TIMEOUT_ENV] = "0.1"
    assert get_ollama_timeout_seconds() == 1.0
    os.environ.pop(OLLAMA_TIMEOUT_ENV, None)


def test_get_ollama_timeout_seconds_clamps_max():
    from backend.main import get_ollama_timeout_seconds, OLLAMA_TIMEOUT_ENV

    os.environ[OLLAMA_TIMEOUT_ENV] = "999"
    assert get_ollama_timeout_seconds() == 30.0
    os.environ.pop(OLLAMA_TIMEOUT_ENV, None)


def test_check_http_target_healthy(monkeypatch):
    import backend.main as main_module

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(main_module.httpx, "get", lambda *a, **kw: FakeResponse())
    healthy, detail = main_module.check_http_target("http://localhost:9999/health")
    assert healthy is True
    assert "200" in detail


def test_check_http_target_unhealthy(monkeypatch):
    import backend.main as main_module

    class FakeResponse:
        status_code = 503

    monkeypatch.setattr(main_module.httpx, "get", lambda *a, **kw: FakeResponse())
    healthy, detail = main_module.check_http_target("http://localhost:9999/health")
    assert healthy is False
    assert "503" in detail


def test_serialize_incident_with_malformed_analysis(db):
    from backend.models import Incident as DBIncident
    from backend.main import serialize_incident
    from datetime import datetime

    inc = DBIncident(
        title="Test incident",
        affected_service_id=1,
        severity="low",
        summary="Some summary text",
        symptoms="Some symptoms text",
        status="open",
        source="manual",
        event_type="incident",
        analysis="NOT_VALID_JSON{{{",
        overview_snapshot="ALSO_INVALID{{",
        created_at=datetime.utcnow(),
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    result = serialize_incident(inc)
    assert result.analysis is None
    assert result.overview_snapshot is None


def test_classification_database_service_type_bonus(client):
    svc = client.post("/api/services", json={
        "name": "postgres",
        "service_type": "database",
        "description": "The main PostgreSQL database",
        "environment": "dev",
        "status": "running",
    }).json()
    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Connection refused",
        "affected_service_id": svc["id"],
        "severity": "critical",
        "symptoms": "Cannot connect to the database server",
    })
    assert resp.status_code == 200
    assert resp.json()["incident_class"] == "database_connectivity"


def test_list_recent_incidents_for_context_with_analysis(client, db):
    import json as json_mod
    from backend.models import Incident as DBIncident
    from backend.main import (
        list_recent_incidents_for_context,
        IncidentServiceContext,
    )
    from datetime import datetime

    svc = client.post("/api/services", json={
        "name": "test-svc-ctx",
        "service_type": "api",
        "description": "Test service for context",
        "environment": "dev",
        "status": "running",
    }).json()

    inc = DBIncident(
        title="Past incident",
        affected_service_id=svc["id"],
        severity="high",
        summary="DB down",
        symptoms="Cannot connect",
        status="resolved",
        source="manual",
        event_type="incident",
        analysis=json_mod.dumps({"incident_class": "database_connectivity"}),
        created_at=datetime.utcnow(),
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    ctx = IncidentServiceContext(
        id=svc["id"],
        name="test-svc-ctx",
        service_type="api",
        environment="dev",
        status="running",
        owner=None,
        url=None,
        health_endpoint=None,
        healthy=True,
        health_detail="ok",
    )
    entries = list_recent_incidents_for_context(db, ctx, "database_connectivity")
    assert len(entries) == 1
    assert entries[0]["incident_class"] == "database_connectivity"


def test_list_recent_incidents_for_context_with_malformed_analysis(db):
    import json as json_mod
    from backend.models import Incident as DBIncident, Service as DBService
    from backend.main import list_recent_incidents_for_context, IncidentServiceContext
    from datetime import datetime

    svc = DBService(
        name="test-svc-malformed",
        service_type="api",
        description="Service for malformed analysis test",
        environment="dev",
        status="running",
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)

    inc = DBIncident(
        title="Past incident with bad analysis",
        affected_service_id=svc.id,
        severity="high",
        summary="Something broke",
        symptoms="Errors everywhere",
        status="resolved",
        source="manual",
        event_type="incident",
        analysis="NOT_VALID_JSON{{{{",
        created_at=datetime.utcnow(),
    )
    db.add(inc)
    db.commit()

    ctx = IncidentServiceContext(
        id=svc.id,
        name="test-svc-malformed",
        service_type="api",
        environment="dev",
        status="running",
        owner=None,
        url=None,
        health_endpoint=None,
        healthy=True,
        health_detail="ok",
    )
    entries = list_recent_incidents_for_context(db, ctx, "database_connectivity")
    assert len(entries) == 1
    assert "incident_class" not in entries[0]


def test_ollama_invalid_confidence_ignored(client, monkeypatch):
    import json as json_mod
    import backend.main as main_module

    monkeypatch.setenv("INCIDENT_ASSISTANT_USE_OLLAMA", "true")

    class InvalidConfidenceResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "response": json_mod.dumps({
                    "suspected_causes": ["Something wrong"],
                    "recommended_checks": ["Check logs"],
                    "suggested_runbook": ["Restart service"],
                    "confidence": "super-confident",
                })
            }

    monkeypatch.setattr(
        main_module.httpx, "post", lambda *a, **kw: InvalidConfidenceResponse()
    )

    svc = client.post("/api/services", json={
        "name": "backend",
        "service_type": "api",
        "description": "A backend service",
        "environment": "dev",
        "status": "running",
    }).json()

    resp = client.post("/api/ai/incidents/analyze", json={
        "summary": "Backend returning errors",
        "affected_service_id": svc["id"],
        "severity": "high",
        "symptoms": "All requests failing",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["suspected_causes"][0] == "Something wrong"
    assert data["confidence"] in {"low", "medium", "high"}
