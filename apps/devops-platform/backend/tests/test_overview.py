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


def test_overview_service_all_environment(client):
    client.post("/api/services", json={
        "name": "shared-svc",
        "service_type": "api",
        "description": "A service available in all environments",
        "environment": "all",
        "status": "running",
    })
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_count"] >= 1
    service_names = [s["name"] for s in data["services"]]
    assert "shared-svc" in service_names


def test_overview_with_healthy_service(client, monkeypatch):
    import backend.main as main_module

    def fake_check_http_target(url):
        return True, "http 200"

    monkeypatch.setattr(main_module, "check_http_target", fake_check_http_target)

    client.post("/api/services", json={
        "name": "healthy-svc",
        "service_type": "api",
        "description": "A service with a health endpoint",
        "environment": "dev",
        "status": "running",
        "health_endpoint": "http://localhost:9999/health",
    })
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    healthy_service = next((s for s in data["services"] if s["name"] == "healthy-svc"), None)
    assert healthy_service is not None
    assert healthy_service["healthy"] is True


def test_overview_service_no_health_target(client):
    client.post("/api/services", json={
        "name": "no-target-svc",
        "service_type": "api",
        "description": "A service without any URL or health endpoint",
        "environment": "dev",
        "status": "running",
    })
    resp = client.get("/api/overview")
    assert resp.status_code == 200
    data = resp.json()
    svc = next((s for s in data["services"] if s["name"] == "no-target-svc"), None)
    assert svc is not None
    assert svc["healthy"] is False
    assert "no health target" in svc["detail"]


def test_overview_db_error(client):
    from sqlalchemy.exc import OperationalError as OpErr
    import backend.main as main_module
    from backend.database import get_db

    class FailingSession:
        def execute(self, *args, **kwargs):
            raise OpErr("SELECT 1", {}, Exception("DB down"))

        def query(self, *args, **kwargs):
            class Q:
                def filter(self, *a, **kw): return self
                def all(self): return []
                def count(self): return 0
            return Q()

    def override():
        yield FailingSession()

    app = main_module.app
    app.dependency_overrides[get_db] = override
    resp = client.get("/api/overview")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["database_status"] == "error"


def test_overview_backfills_production_baseline(client, monkeypatch):
    import backend.main as main_module

    def fake_check_http_target(url):
        return True, "http 200"

    monkeypatch.setattr(main_module, "APP_ENVIRONMENT", "production")
    monkeypatch.setattr(main_module, "ENV_SHORT", "production")
    monkeypatch.setattr(main_module, "check_http_target", fake_check_http_target)

    resp = client.get("/api/overview")

    assert resp.status_code == 200
    data = resp.json()
    assert data["project_count"] == 2
    assert data["featured_project_count"] == 2
    assert data["service_count"] == 3
    assert data["healthy_service_count"] == 3
    assert {service["name"] for service in data["services"]} == {
        "backend",
        "frontend",
        "monitor-worker",
    }
