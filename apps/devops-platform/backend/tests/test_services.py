SAMPLE_SERVICE = {
    "name": "test-service",
    "service_type": "api",
    "description": "A test service for unit tests",
    "url": "http://localhost:8000",
    "port": 8000,
    "environment": "dev",
    "status": "running",
}


def test_create_service(client):
    resp = client.post("/api/services", json=SAMPLE_SERVICE)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test-service"
    assert data["id"] is not None


def test_list_services_empty(client):
    resp = client.get("/api/services")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_services(client):
    client.post("/api/services", json=SAMPLE_SERVICE)
    resp = client.get("/api/services")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_service(client):
    create = client.post("/api/services", json=SAMPLE_SERVICE)
    sid = create.json()["id"]
    resp = client.get(f"/api/services/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test-service"


def test_get_service_not_found(client):
    resp = client.get("/api/services/999")
    assert resp.status_code == 404


def test_update_service(client):
    create = client.post("/api/services", json=SAMPLE_SERVICE)
    sid = create.json()["id"]
    updated = {**SAMPLE_SERVICE, "description": "Updated description text"}
    resp = client.put(f"/api/services/{sid}", json=updated)
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description text"


def test_update_service_not_found(client):
    resp = client.put("/api/services/999", json=SAMPLE_SERVICE)
    assert resp.status_code == 404


def test_delete_service(client):
    create = client.post("/api/services", json=SAMPLE_SERVICE)
    sid = create.json()["id"]
    resp = client.delete(f"/api/services/{sid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/services/{sid}")
    assert resp.status_code == 404


def test_delete_service_not_found(client):
    resp = client.delete("/api/services/999")
    assert resp.status_code == 404


def test_service_port_validation(client):
    bad = {**SAMPLE_SERVICE, "port": 99999}
    resp = client.post("/api/services", json=bad)
    assert resp.status_code == 422


def test_list_services_backfills_production_baseline(client, monkeypatch):
    import backend.main as main_module

    monkeypatch.setattr(main_module, "APP_ENVIRONMENT", "production")
    monkeypatch.setattr(main_module, "ENV_SHORT", "production")

    resp = client.get("/api/services")

    assert resp.status_code == 200
    assert {service["name"] for service in resp.json()} == {
        "backend",
        "frontend",
        "monitor-worker",
        "nginx",
    }
