def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_api_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_health_degraded_on_db_error(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    import backend.main as main_module

    original_get_db = main_module.get_db

    def failing_db():
        session = next(original_get_db())

        class FailingSession:
            def execute(self, *args, **kwargs):
                raise OperationalError("SELECT 1", {}, Exception("DB down"))

        yield FailingSession()

    monkeypatch.setattr(main_module, "get_db", failing_db)
    from backend.database import get_db
    from backend.main import app

    app.dependency_overrides[get_db] = failing_db
    resp = client.get("/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["database"] == "error"
