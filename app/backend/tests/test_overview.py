def test_overview_empty(client):
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database_status"] == "ok"
    assert data["project_count"] == 0
    assert data["service_count"] == 0
    assert "build" in data
    assert "component_versions" in data["build"]


def test_overview_with_data(client):
    client.post("/api/portfolio/projects", json={
        "title": "Overview Test Project",
        "description": "A project for overview testing",
        "technologies": ["Python"],
        "featured": True,
    })
    client.post("/api/services", json={
        "name": "test-svc",
        "service_type": "api",
        "description": "A test service",
        "environment": "dev",
        "status": "running",
    })
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_count"] == 1
    assert data["featured_project_count"] == 1
    assert data["service_count"] == 1
    assert len(data["services"]) == 1
