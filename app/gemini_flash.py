from typing import List, Dict, Any
from app.services.comic_service import comic_service

def generate_outline(user_prompt: str) -> List[Dict[str, Any]]:
    """
    Project Specification conforming facade:
    Uses Gemini Flash AI model to generate a structured 5-panel comic outline.
    """
    return comic_service.story_provider.generate_outline(
        prompt=user_prompt,
        character_name="Hero",
        character_appearance="",
        setting="Fantasy Forest",
        tone="Dramatic",
        art_style="Classic Comic Book",
        panel_count=5
    )
