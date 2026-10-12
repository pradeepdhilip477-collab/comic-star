import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "story_provider" in data
    assert "image_provider" in data

def test_homepage_rendering(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "ComicCraft" in response.text
    assert "Your imagination." in response.text

def test_studio_rendering(client):
    response = client.get("/studio")
    assert response.status_code == 200
    assert "Story Configuration" in response.text
    assert "Generate My Comic" in response.text

def test_export_success_rendering(client):
    response = client.get("/export-success?comic_title=Test%20Story")
    assert response.status_code == 200
    assert "Comic Exported Successfully!" in response.text
    assert "Test Story" in response.text

def test_test_image_route(client):
    response = client.get("/test-image?prompt=A%20dramatic%20sunset")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "path" in data
