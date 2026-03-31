SAMPLE_PROJECT = {
    "title": "Test Project",
    "description": "A test project for unit tests",
    "technologies": ["Python", "FastAPI"],
    "github_url": "https://github.com/test/repo",
    "category": "Platform",
    "status": "active",
    "featured": False,
}


def test_create_project(client):
    resp = client.post("/api/portfolio/projects", json=SAMPLE_PROJECT)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Project"
    assert data["technologies"] == ["Python", "FastAPI"]
    assert data["id"] is not None


def test_list_projects_empty(client):
    resp = client.get("/api/portfolio/projects")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_projects(client):
    client.post("/api/portfolio/projects", json=SAMPLE_PROJECT)
    resp = client.get("/api/portfolio/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_project(client):
    create = client.post("/api/portfolio/projects", json=SAMPLE_PROJECT)
    pid = create.json()["id"]
    resp = client.get(f"/api/portfolio/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Project"


def test_get_project_not_found(client):
    resp = client.get("/api/portfolio/projects/999")
    assert resp.status_code == 404


def test_update_project(client):
    create = client.post("/api/portfolio/projects", json=SAMPLE_PROJECT)
    pid = create.json()["id"]
    updated = {**SAMPLE_PROJECT, "title": "Updated Title"}
    resp = client.put(f"/api/portfolio/projects/{pid}", json=updated)
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


def test_update_project_not_found(client):
    resp = client.put("/api/portfolio/projects/999", json=SAMPLE_PROJECT)
    assert resp.status_code == 404


def test_delete_project(client):
    create = client.post("/api/portfolio/projects", json=SAMPLE_PROJECT)
    pid = create.json()["id"]
    resp = client.delete(f"/api/portfolio/projects/{pid}")
    assert resp.status_code == 204
    # Soft-deleted: should not appear in listing
    resp = client.get(f"/api/portfolio/projects/{pid}")
    assert resp.status_code == 404


def test_delete_project_not_found(client):
    resp = client.delete("/api/portfolio/projects/999")
    assert resp.status_code == 404


def test_create_project_validation(client):
    bad = {"title": "X", "description": "short", "technologies": []}
    resp = client.post("/api/portfolio/projects", json=bad)
    assert resp.status_code == 422
