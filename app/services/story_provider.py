import json
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class StoryProvider(ABC):
    @abstractmethod
    def generate_outline(self, prompt: str, character_name: str, character_appearance: str,
                         setting: str, tone: str, art_style: str, panel_count: int) -> List[Dict[str, Any]]:
        """Generate structured panel outlines"""
        pass

    @abstractmethod
    def generate_story(self, outline: List[Dict[str, Any]], character_name: str,
                       setting: str, tone: str) -> List[Dict[str, Any]]:
        """Generate dialogue and narration for each panel"""
        pass

class GeminiStoryProvider(StoryProvider):
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured in environment")
        
        from google import genai
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.flash_model = settings.GEMINI_FLASH_MODEL
        self.pro_model = settings.GEMINI_PRO_MODEL

    def generate_outline(self, prompt: str, character_name: str, character_appearance: str,
                         setting: str, tone: str, art_style: str, panel_count: int) -> List[Dict[str, Any]]:
        from google.genai import types
        
        system_instruction = (
            "You are a master comic-book director, illustrator, and storyboard architect. "
            "You create visually dynamic, emotionally engaging graphic novel sequences. "
            "Every panel must show distinct camera framing, meaningful action with visual verbs, "
            "and expressive character poses. Never repeat backgrounds or generic sunset landscapes. "
            "Output strictly valid JSON."
        )

        char_desc = (
            f"HERO PROFILE: Name: '{character_name}'. Visual Appearance: {character_appearance}."
            if character_appearance else f"HERO PROFILE: Name: '{character_name}'."
        )

        user_prompt = f"""
Create a dramatic, story-specific {panel_count}-panel comic storyboard for:
STORY PREMISE: "{prompt}"
{char_desc}
SETTING: "{setting}"
TONE: "{tone}"
ART STYLE: "{art_style}"

REQUIRED COMIC PROGRESSION RULES:
1. Each panel MUST have a completely distinct camera framing:
   - Panel 1: Establishing wide angle shot (introducing setting and character arriving).
   - Panel 2: Medium discovery/interaction shot (character encountering or opening something specific).
   - Panel 3: Dynamic high-action angle (sudden activation, conflict, or climax surge).
   - Panel 4: Intense close-up or low-angle shot (problem-solving, tension, overcoming the hurdle).
   - Panel 5: Wide climactic resolution shot (the aftermath, restored harmony, triumphant revelation).
2. Every panel's "image_prompt" must be a rich, descriptive prompt for an AI illustrator including:
   - Camera angle (wide, medium, close-up, low-angle, dutch angle)
   - Specific character action (using strong visual verbs like unbolting, leaping, calibrating, clutching)
   - Facial expression and body language
   - Specific environment details (e.g. rusted consoles, glowing crystal geodes, towering cyber arches)
   - Consistent character attire and features from HERO PROFILE
   - Color lighting direction: warm coral, amber, earthy tones, rich ink outlines, comic book color palette
3. DO NOT generate repetitive sunset silhouettes or static standing poses.

Return a valid JSON array of exactly {panel_count} objects with:
- "panel": integer (1 to {panel_count})
- "title": punchy comic panel title
- "scene_description": what specifically happens visually in this panel
- "main_character_action": what {character_name} is specifically doing
- "image_prompt": detailed text-to-image prompt (70-100 words) describing composition, character, action, lighting, and {art_style} style
- "narrative_purpose": narrative arc purpose

Format:
[
  {{
    "panel": 1,
    "title": "...",
    "scene_description": "...",
    "main_character_action": "...",
    "image_prompt": "...",
    "narrative_purpose": "..."
  }}
]
"""
        models_to_try = [self.flash_model, "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        models_to_try = list(dict.fromkeys(models_to_try))
        
        last_err = None
        for model_id in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.7,
                    )
                )
                text = response.text.strip()
                data = json.loads(text)
                if isinstance(data, dict) and "panels" in data:
                    return data["panels"]
                return data
            except Exception as e:
                logger.warning(f"Gemini generate_outline failed with model '{model_id}': {e}")
                last_err = e
        raise last_err

    def generate_story(self, outline: List[Dict[str, Any]], character_name: str,
                       setting: str, tone: str) -> List[Dict[str, Any]]:
        from google.genai import types
        
        system_instruction = (
            "You are an acclaimed comic book scriptwriter. You write snappy dialogue, "
            "punchy caption boxes, and dramatic inner narration. "
            "Output strictly valid JSON."
        )

        formatted_outline = json.dumps(outline, indent=2)
        user_prompt = f"""
Given this comic panel outline:
{formatted_outline}

Write the dialogue and narration for each panel.
Character Name: {character_name}
Setting: {setting}
Tone: {tone}

Rules:
- "caption": short ambient caption establishing place or time (e.g., "The Forgotten Scriptorium, deep below the surface...")
- "narration": concise comic narrative voice (1-2 sentences capturing tension and story progress)
- "dialogue": authentic in-character spoken dialogue attributed with character name, e.g. "{character_name}: 'We only have one shot at this!'"
  (If the panel is a solo silent moment or reaction, dialogue can be an exclamation or empty)

Return a valid JSON array of objects, one per panel with:
- "panel": integer (matching outline)
- "caption": string
- "narration": string
- "dialogue": string

Format:
[
  {{
    "panel": 1,
    "caption": "...",
    "narration": "...",
    "dialogue": "..."
  }}
]
"""
        models_to_try = [self.pro_model, self.flash_model, "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        models_to_try = list(dict.fromkeys(models_to_try))
        
        last_err = None
        for model_id in models_to_try:
            try:
                response = self.client.models.generate_content(
                    model=model_id,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        temperature=0.8,
                    )
                )
                text = response.text.strip()
                data = json.loads(text)
                if isinstance(data, dict) and "panels" in data:
                    return data["panels"]
                return data
            except Exception as e:
                logger.warning(f"Gemini generate_story failed with model '{model_id}': {e}")
                last_err = e
        raise last_err


class DeterministicStoryProvider(StoryProvider):
    """
    High-fidelity offline storytelling engine providing rich, dynamic, deterministic
    comic storylines tailored to user inputs. Explicitly tagged as demo mode.
    """
    def generate_outline(self, prompt: str, character_name: str, character_appearance: str,
                         setting: str, tone: str, art_style: str, panel_count: int) -> List[Dict[str, Any]]:
        appearance = character_appearance or "leather aviator jacket, brass goggles, and a steadfast expression"
        
        # Analyze prompt keywords for customized story beats
        p_clean = prompt.strip()
        words = p_clean.split()
        concept = " ".join(words[:5]) if words else "the ancient discovery"

        stages = [
            (
                "The Threshold",
                f"Wide establishing shot. {character_name} navigates the towering arches of {setting}, studying an illuminated holographic map.",
                f"{character_name} surveys the uncharted route ahead.",
                f"Wide cinematic shot, {art_style} style, comic art. {character_name} with {appearance} stands amidst the vast architecture of {setting}. Deep dramatic shadows, warm amber lighting, sharp ink outlines, establishing scene.",
                "Act I: Setup and arrival"
            ),
            (
                "The Discovery",
                f"Medium shot. {character_name} uncovers a hidden sealed chamber in {setting}, wiping dust from a glowing mechanism.",
                f"{character_name} reaches forward with gloved hand to inspect the ancient relic.",
                f"Medium camera angle, {art_style} style, comic art. {character_name} with {appearance} leans in toward an intricate glowing device in {setting}. Expressive focused eyes, reflective highlights, vibrant coral and teal hues, ink cross-hatching.",
                "Act I: Inciting Incident"
            ),
            (
                "The Surge",
                f"Dynamic action shot. Energy crackles through the chamber as alarms flare, creating an intense {tone.lower()} crisis.",
                f"{character_name} leaps into a defensive stance, shielding against arcing lightning bolts.",
                f"Dynamic action composition, low camera angle, {art_style} style, comic art. Powerful energy explosion and motion lines in {setting}. {character_name} with {appearance} in an athletic defensive lunge. Crimson and electric blue sparks, intense facial grit, comic speed lines.",
                "Act II: Climax and confrontation"
            ),
            (
                "The Breakthrough",
                f"Tight tension shot. In the heart of the storm, {character_name} works furiously to align the energy conduits and stabilize the core.",
                f"{character_name} calibrates the control nodes with precision.",
                f"Close-up dramatic shot, {art_style} style, comic art. {character_name} with {appearance} intensely tuning the glowing power core in {setting}. Sweat on brow, illuminated by bright gold sparks, sharp comic inking, emotional determination.",
                "Act II: Turning point"
            ),
            (
                "The Dawn Revealed",
                f"Panoramic wide shot. The mechanism awakens fully, projecting a brilliant celestial beacon across the entirety of {setting}.",
                f"{character_name} stands triumphant, smiling as warmth returns to the realm.",
                f"Triumphant wide panoramic shot, {art_style} style, comic art. Radiant golden and coral light washes over {setting}. {character_name} with {appearance} stands victorious, holding the activated artifact aloft. Majestic atmosphere, celebratory comic illustration.",
                "Act III: Resolution and reward"
            )
        ]
        
        panels = []
        for i in range(min(panel_count, len(stages))):
            title, desc, action, img_prompt, purpose = stages[i]
            panels.append({
                "panel": i + 1,
                "title": f"Panel {i+1}: {title}",
                "scene_description": desc,
                "main_character_action": action,
                "image_prompt": img_prompt,
                "narrative_purpose": purpose
            })
            
        while len(panels) < panel_count:
            idx = len(panels) + 1
            panels.append({
                "panel": idx,
                "title": f"Panel {idx}: Journey Beyond",
                "scene_description": f"{character_name} documents the miraculous discovery in {setting}.",
                "main_character_action": f"{character_name} takes notes on the energized phenomenon.",
                "image_prompt": f"Medium shot, {art_style} style, comic art. {character_name} with {appearance} in {setting}, observant and focused. Rich warm comic palette.",
                "narrative_purpose": "Extended exploration"
            })
        return panels

    def generate_story(self, outline: List[Dict[str, Any]], character_name: str,
                       setting: str, tone: str) -> List[Dict[str, Any]]:
        results = []
        templates = [
            (
                f"{setting.upper()} — SECTOR ZERO",
                f"Legends whispered that no traveler had returned from {setting}. But {character_name} never trusted rumors over hard facts.",
                f"{character_name}: 'The coordinates match. It really exists...'"
            ),
            (
                f"DEEP BELOW THE SURFACE",
                f"Centuries of dust gave way beneath careful fingers, revealing technology older than the empire itself.",
                f"{character_name}: 'Careful now... one wrong touch and the whole network could collapse.'"
            ),
            (
                f"ENERGY CRITICAL",
                f"Without warning, dormant power surged through the grid with deafening intensity!",
                f"{character_name}: 'Hold steady! I am not losing this ground now!'"
            ),
            (
                f"THE TURNING SECOND",
                f"Through blinding arcs and shuddering walls, instinct and training found the perfect frequency.",
                f"{character_name}: 'Just need three more seconds... synchronized!'"
            ),
            (
                f"NEW DAWN",
                f"A warm hum echoed across {setting} as ancient light pierced the darkness, signaling the start of a new era.",
                f"{character_name}: 'We did it. The legend was real all along.'"
            )
        ]
        
        for i, panel in enumerate(outline):
            t_idx = i % len(templates)
            caption, narration, dialogue = templates[t_idx]
            results.append({
                "panel": panel.get("panel", i + 1),
                "caption": caption,
                "narration": narration,
                "dialogue": dialogue
            })
        return results
