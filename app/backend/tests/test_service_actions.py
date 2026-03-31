def _create_service(client, name="monitor-worker"):
    return client.post("/api/services", json={
        "name": name,
        "service_type": "worker",
        "description": "A manageable test service",
        "environment": "dev",
        "status": "running",
    }).json()


def test_queue_restart_action(client):
    svc = _create_service(client, "monitor-worker")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "restart"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "restart"
    assert data["status"] == "queued"
    assert data["job_id"] is not None


def test_queue_stop_action(client):
    svc = _create_service(client, "monitor-worker")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "stop"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "stop"


def test_queue_start_action(client):
    svc = _create_service(client, "monitor-worker")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "start"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "start"


def test_action_not_allowed_for_control_plane(client):
    svc = _create_service(client, "backend")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "stop"})
    assert resp.status_code == 400
    assert "not allowed" in resp.json()["detail"]


def test_action_restart_allowed_for_control_plane(client):
    svc = _create_service(client, "backend")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "restart"})
    assert resp.status_code == 200
    assert resp.json()["action"] == "restart"


def test_action_on_uncontrolled_service(client):
    svc = _create_service(client, "custom-thing")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "restart"})
    assert resp.status_code == 400
    assert "observable only" in resp.json()["detail"]


def test_action_invalid_verb(client):
    svc = _create_service(client, "monitor-worker")
    resp = client.post(f"/api/services/{svc['id']}/actions", json={"action": "destroy"})
    assert resp.status_code == 422


def test_action_on_missing_service(client):
    resp = client.post("/api/services/999/actions", json={"action": "restart"})
    assert resp.status_code == 404


def test_duplicate_action_returns_existing(client):
    svc = _create_service(client, "monitor-worker")
    first = client.post(f"/api/services/{svc['id']}/actions", json={"action": "restart"})
    second = client.post(f"/api/services/{svc['id']}/actions", json={"action": "restart"})
    assert second.status_code == 200
    assert second.json()["job_id"] == first.json()["job_id"]
    assert "already queued" in second.json()["detail"]


def test_list_action_jobs(client):
    svc = _create_service(client, "monitor-worker")
    client.post(f"/api/services/{svc['id']}/actions", json={"action": "restart"})
    resp = client.get("/api/service-action-jobs")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
