import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.schemas import PromptRequest
from app.main import app

client = TestClient(app)

def test_prompt_request_validation():
    # Valid request
    valid = PromptRequest(
        prompt="A brave knight protects a village",
        character_name="Sir Arthur",
        setting="Medieval Village",
        tone="Adventure",
        art_style="Classic Comic Book",
        panel_count=5
    )
    assert valid.character_name == "Sir Arthur"
    
    # Too short prompt should fail
    with pytest.raises(ValidationError):
        PromptRequest(
            prompt="Hi",
            character_name="Sir Arthur"
        )

def test_api_comic_creation_and_polling():
    payload = {
        "prompt": "An AI researcher builds a thinking robot in a secret laboratory",
        "character_name": "Dr. Elen",
        "character_appearance": "White lab coat, blue glasses",
        "setting": "Cyberpunk Metropolis",
        "tone": "Sci-Fi",
        "art_style": "Anime",
        "panel_count": 3
    }
    
    # 1. Trigger generation via JSON API
    res = client.post("/api/comics/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    comic_id = data["comic_id"]
    assert comic_id is not None
    assert data["status"] == "processing"
    
    # 2. Check status endpoint immediately
    status_res = client.get(f"/api/comics/{comic_id}/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["id"] == comic_id
    assert status_data["status"] in ["pending", "processing", "completed"]
    assert "current_stage" in status_data
