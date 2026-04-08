def _create_service(client, name="test-service"):
    return client.post("/api/services", json={
        "name": name,
        "service_type": "api",
        "description": "A test service",
        "environment": "dev",
        "status": "running",
    }).json()


def _create_incident(client, service_id):
    return client.post("/api/incidents", json={
        "title": "Test incident title",
        "affected_service_id": service_id,
        "severity": "medium",
        "summary": "Something went wrong with the service",
        "symptoms": "Service returning errors",
        "status": "open",
    }).json()


def test_create_incident(client):
    svc = _create_service(client)
    resp = client.post("/api/incidents", json={
        "title": "Test incident title",
        "affected_service_id": svc["id"],
        "severity": "high",
        "summary": "Database connection refused on startup",
        "symptoms": "Backend returns 500 errors",
        "status": "open",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test incident title"
    assert data["severity"] == "high"


def test_create_incident_bad_service(client):
    resp = client.post("/api/incidents", json={
        "title": "Test incident title",
        "affected_service_id": 999,
        "severity": "medium",
        "summary": "Something went wrong",
        "symptoms": "Service returning errors",
        "status": "open",
    })
    assert resp.status_code == 404


def test_list_incidents_empty(client):
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_incidents(client):
    svc = _create_service(client)
    _create_incident(client, svc["id"])
    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_incident(client):
    svc = _create_service(client)
    inc = _create_incident(client, svc["id"])
    resp = client.get(f"/api/incidents/{inc['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test incident title"


def test_get_incident_not_found(client):
    resp = client.get("/api/incidents/999")
    assert resp.status_code == 404


def test_update_incident(client):
    svc = _create_service(client)
    inc = _create_incident(client, svc["id"])
    updated = {
        "title": "Updated incident",
        "affected_service_id": svc["id"],
        "severity": "critical",
        "summary": "Updated summary text here",
        "symptoms": "Updated symptoms text here",
        "status": "investigating",
    }
    resp = client.put(f"/api/incidents/{inc['id']}", json=updated)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated incident"
    assert resp.json()["severity"] == "critical"


def test_update_incident_not_found(client):
    resp = client.put("/api/incidents/999", json={
        "title": "X" * 5,
        "affected_service_id": 1,
        "severity": "low",
        "summary": "Test summary text",
        "symptoms": "Test symptoms text",
        "status": "open",
    })
    assert resp.status_code == 404


def test_delete_incident(client):
    svc = _create_service(client)
    inc = _create_incident(client, svc["id"])
    resp = client.delete(f"/api/incidents/{inc['id']}")
    assert resp.status_code == 204
    resp = client.get(f"/api/incidents/{inc['id']}")
    assert resp.status_code == 404


def test_delete_incident_not_found(client):
    resp = client.delete("/api/incidents/999")
    assert resp.status_code == 404


def test_severity_validation(client):
    svc = _create_service(client)
    resp = client.post("/api/incidents", json={
        "title": "Bad severity test",
        "affected_service_id": svc["id"],
        "severity": "extreme",
        "summary": "Test summary text here",
        "symptoms": "Test symptoms text here",
        "status": "open",
    })
    assert resp.status_code == 422


def test_update_non_manual_incident_is_forbidden(client, db):
    from backend.models import Incident as DBIncident
    from datetime import datetime

    svc = _create_service(client)
    log_entry = DBIncident(
        title="monitor-worker restart requested from portal",
        affected_service_id=svc["id"],
        severity="low",
        summary="Portal queued a restart action.",
        symptoms="Operator requested a service action.",
        status="investigating",
        source="service-action",
        event_type="service_restart_requested",
        created_at=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    resp = client.put(f"/api/incidents/{log_entry.id}", json={
        "title": "Updated title here",
        "affected_service_id": svc["id"],
        "severity": "medium",
        "summary": "Test summary text",
        "symptoms": "Test symptoms text",
        "status": "open",
    })
    assert resp.status_code == 400
    assert "read-only" in resp.json()["detail"]


def test_delete_non_manual_incident_is_forbidden(client, db):
    from backend.models import Incident as DBIncident
    from datetime import datetime

    svc = _create_service(client)
    log_entry = DBIncident(
        title="monitor-worker stop requested from portal",
        affected_service_id=svc["id"],
        severity="low",
        summary="Portal queued a stop action.",
        symptoms="Operator requested a service action.",
        status="investigating",
        source="service-action",
        event_type="service_stop_requested",
        created_at=datetime.utcnow(),
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    resp = client.delete(f"/api/incidents/{log_entry.id}")
    assert resp.status_code == 400
    assert "read-only" in resp.json()["detail"]


def test_update_incident_bad_service(client):
    svc = _create_service(client)
    inc = _create_incident(client, svc["id"])
    resp = client.put(f"/api/incidents/{inc['id']}", json={
        "title": "Updated incident",
        "affected_service_id": 999,
        "severity": "low",
        "summary": "Some summary here",
        "symptoms": "Some symptoms here",
        "status": "open",
    })
    assert resp.status_code == 404


def test_update_incident_with_overview_snapshot(client):
    svc = _create_service(client)
    inc = _create_incident(client, svc["id"])
    resp = client.put(f"/api/incidents/{inc['id']}", json={
        "title": "Updated incident title",
        "affected_service_id": svc["id"],
        "severity": "high",
        "summary": "Updated summary with snapshot",
        "symptoms": "Updated symptoms here",
        "status": "investigating",
        "overview_snapshot": {"backend_status": "ok", "service_count": 1},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overview_snapshot"]["backend_status"] == "ok"


def test_incident_status_validation(client):
    svc = _create_service(client)
    resp = client.post("/api/incidents", json={
        "title": "Bad status test",
        "affected_service_id": svc["id"],
        "severity": "medium",
        "summary": "Test summary text",
        "symptoms": "Test symptoms text",
        "status": "closed",
    })
    assert resp.status_code == 422
