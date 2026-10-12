from typing import List, Dict, Any
from app.services.comic_service import comic_service

def generate_story(outline: list) -> str:
    """
    Project Specification conforming facade:
    Uses Gemini Pro AI model to expand panel outlines into narration and character dialogues.
    """
    stories = comic_service.story_provider.generate_story(
        outline=outline,
        character_name="Hero",
        setting="Fantasy Forest",
        tone="Dramatic"
    )
    # Return formatted single string if required by legacy signature
    parts = []
    for s in stories:
        parts.append(f"**Panel {s.get('panel')}**\nCaption: {s.get('caption')}\nNarration: {s.get('narration')}\nDialogue: {s.get('dialogue')}")
    return "\n\n".join(parts)
