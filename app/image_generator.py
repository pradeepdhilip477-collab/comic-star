import os
import re
from app.config import settings
from app.services.comic_service import comic_service

def sanitize_filename(prompt: str) -> str:
    clean = re.sub(r"[^\w\s-]", "", prompt).strip().lower()
    return re.sub(r"[-\s]+", "_", clean)[:30] + ".jpg"

def generate_image(prompt: str, filename: str = None) -> str:
    """
    Project Specification conforming facade:
    Generates a comic illustration based on the image prompt and saves to static/panels.
    """
    if not filename:
        filename = sanitize_filename(prompt)
    output_path = settings.PANELS_DIR / filename
    saved_path = comic_service.image_provider.generate_image(
        prompt=prompt,
        output_path=str(output_path),
        character_name="Hero",
        art_style="Classic Comic Book",
        panel_number=1
    )
    return str(saved_path)
