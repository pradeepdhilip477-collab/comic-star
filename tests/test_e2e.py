import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Comic, Panel

client = TestClient(app)

@pytest.mark.asyncio
async def test_complete_end_to_end_comic_generation():
    """
    Tests complete lifecycle:
    Form submission -> Asynchronous background worker execution ->
    Panel creation -> SQLite persistence -> PDF verification -> Regeneration API
    """
    form_data = {
        "prompt": "A courageous fox embarks on an expedition through crystal caverns to rescue an ancient starry compass",
        "character_name": "Free",
        "character_appearance": "Bright orange fur, scout vest with compass emblem",
        "setting": "Crystal Caverns",
        "tone": "Adventure",
        "style": "Classic Comic Book",
        "panel_count": 5
    }
    
    # 1. Submit Form
    res = client.post("/generate", data=form_data, follow_redirects=False)
    assert res.status_code == 303
    redirect_url = res.headers["location"]
    comic_id = redirect_url.split("/comic/")[1]
    assert comic_id is not None
    
    # Wait for the background worker to finish (up to 45s for network image generation)
    db = SessionLocal()
    max_wait = 45
    completed = False
    
    for _ in range(max_wait):
        await asyncio.sleep(1)
        comic = db.query(Comic).filter(Comic.id == comic_id).first()
        if comic and comic.status == "completed":
            completed = True
            break
            
    assert completed, f"Generation did not complete in time, status: {comic.status}, stage: {comic.current_stage}"
    
    # 2. Check Database records
    assert comic.status == "completed"
    assert comic.stage_percent == 100
    assert comic.pdf_path is not None
    assert comic.generation_mode in ["demo_mode", "ai_live", "ai_partial"]
    
    panels = db.query(Panel).filter(Panel.comic_id == comic_id).order_by(Panel.panel_number).all()
    assert len(panels) == 5
    for p in panels:
        assert p.image_path is not None
        assert p.title is not None
        assert p.dialogue is not None
        assert p.narration is not None
        
    # 3. Check Web Page Rendering for this Comic
    reader_res = client.get(f"/comic/{comic_id}")
    assert reader_res.status_code == 200
    assert comic.title in reader_res.text
    assert "Free" in reader_res.text
    assert "Download Comic PDF" in reader_res.text
    
    # 4. Check PDF Download Endpoint
    pdf_res = client.get(f"/api/comics/{comic_id}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 5000
    assert pdf_res.content[:4] == b"%PDF"
    
    # 5. Test Regeneration of Panel 1
    panel_1 = panels[0]
    regen_res = client.post(
        f"/api/comics/{comic_id}/panels/{panel_1.id}/regenerate",
        json={"custom_prompt": "A close up heroic stance with shining crystal reflection"}
    )
    assert regen_res.status_code == 200
    regen_data = regen_res.json()
    assert regen_data["success"] is True
    assert "regen" in regen_data["new_image_path"]
    
    db.close()
