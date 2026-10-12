import os
import pytest
from pathlib import Path
from app.services.story_provider import DeterministicStoryProvider
from app.services.image_provider import CanvasIllustratorImageProvider
from app.services.layout_builder import build_comic_layout
from app.services.pdf_service import save_pdf

def test_deterministic_story_outline():
    provider = DeterministicStoryProvider()
    outlines = provider.generate_outline(
        prompt="A space traveler lands on a crystal planet",
        character_name="Zara",
        character_appearance="Silver spacesuit",
        setting="Crystal Planet",
        tone="Sci-Fi",
        art_style="Classic Comic Book",
        panel_count=5
    )
    assert len(outlines) == 5
    assert outlines[0]["panel"] == 1
    assert "Zara" in outlines[0]["image_prompt"]
    assert "image_prompt" in outlines[0]
    assert "scene_description" in outlines[0]

def test_deterministic_story_dialogue():
    provider = DeterministicStoryProvider()
    outlines = provider.generate_outline("Hero quest", "Leo", "", "Forest", "Adventure", "Anime", 5)
    stories = provider.generate_story(outlines, "Leo", "Forest", "Adventure")
    assert len(stories) == 5
    assert "caption" in stories[0]
    assert "narration" in stories[0]
    assert "dialogue" in stories[0]
    assert "Leo" in stories[0]["dialogue"]

def test_canvas_image_generator(tmp_path):
    provider = CanvasIllustratorImageProvider()
    out_file = tmp_path / "panel_1.jpg"
    saved = provider.generate_image("A hero stands ready", str(out_file), "Hero", "Classic Comic Book", 1)
    assert os.path.exists(saved)
    assert os.path.getsize(saved) > 1000

def test_layout_and_pdf_generation(tmp_path):
    story_provider = DeterministicStoryProvider()
    img_provider = CanvasIllustratorImageProvider()
    
    outlines = story_provider.generate_outline("Mystery in the fog", "Detective Holmes", "", "London", "Mystery", "Watercolor", 3)
    stories = story_provider.generate_story(outlines, "Detective Holmes", "London", "Mystery")
    
    img_paths = []
    for i in range(1, 4):
        p_path = tmp_path / f"panel_{i}.jpg"
        img_provider.generate_image(f"Scene {i}", str(p_path), "Holmes", "Watercolor", i)
        img_paths.append(str(p_path))
        
    layout = build_comic_layout(img_paths, stories, outlines)
    assert len(layout) == 3
    assert layout[0]["panel"] == 1
    assert layout[0]["raw_image_path"] == img_paths[0]
    
    pdf_path = save_pdf(layout, comic_title="Mystery in London", comic_id="test_pdf_comic")
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 5000
    
    # Check PDF magic bytes '%PDF'
    with open(pdf_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"
