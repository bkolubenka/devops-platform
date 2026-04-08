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


def test_overview_db_error(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    import backend.main as main_module

    original_compute = main_module.compute_overview

    def failing_compute(db):
        from sqlalchemy import text
        try:
            db.execute(text("SELECT 1 FROM nonexistent_table_xyz"))
        except Exception:
            pass
        return original_compute(db)

    # Monkeypatch the overview to force a DB exception path
    from sqlalchemy.exc import OperationalError as OpErr

    class FailingSession:
        def execute(self, *args, **kwargs):
            raise OpErr("SELECT 1", {}, Exception("DB down"))

        def query(self, *args, **kwargs):
            # Return a minimal stub so the rest of the function works
            class Q:
                def filter(self, *a, **kw): return self
                def all(self): return []
                def count(self): return 0
            return Q()

    original_get_db = main_module.get_db
    from backend.database import get_db

    def override():
        yield FailingSession()

    app = main_module.app
    app.dependency_overrides[get_db] = override
    resp = client.get("/api/overview")
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = lambda: iter([next(original_get_db())])
    assert resp.status_code == 200
    assert resp.json()["database_status"] == "error"
