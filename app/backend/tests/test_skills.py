SAMPLE_SKILL = {"name": "Python", "level": 5, "category": "Languages"}


def test_create_skill(client):
    resp = client.post("/api/portfolio/skills", json=SAMPLE_SKILL)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Python"
    assert data["level"] == 5


def test_list_skills_empty(client):
    resp = client.get("/api/portfolio/skills")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_skills(client):
    client.post("/api/portfolio/skills", json=SAMPLE_SKILL)
    resp = client.get("/api/portfolio/skills")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_skill_level_validation(client):
    bad = {"name": "X", "level": 6, "category": "Languages"}
    resp = client.post("/api/portfolio/skills", json=bad)
    assert resp.status_code == 422

    bad2 = {"name": "X", "level": 0, "category": "Languages"}
    resp = client.post("/api/portfolio/skills", json=bad2)
    assert resp.status_code == 422
