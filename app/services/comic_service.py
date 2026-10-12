import os
import uuid
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Comic, Panel, SessionLocal
from app.schemas import PromptRequest
from app.services.story_provider import GeminiStoryProvider, DeterministicStoryProvider
from app.services.image_provider import (
    PollinationsAIImageProvider,
    HFInferenceImageProvider, 
    LocalDiffusersImageProvider, 
    CanvasIllustratorImageProvider
)
from app.services.layout_builder import build_comic_layout
from app.services.pdf_service import save_pdf

logger = logging.getLogger(__name__)

class ComicService:
    def __init__(self):
        # Resolve Story Provider
        if settings.GEMINI_API_KEY:
            try:
                self.story_provider = GeminiStoryProvider()
                self.story_provider_name = f"google-genai ({settings.GEMINI_FLASH_MODEL})"
                self.is_story_live = True
            except Exception as e:
                logger.warning(f"Failed to initialize GeminiStoryProvider: {e}. Falling back to DeterministicStoryProvider.")
                self.story_provider = DeterministicStoryProvider()
                self.story_provider_name = "offline-demo-storyteller"
                self.is_story_live = False
        else:
            self.story_provider = DeterministicStoryProvider()
            self.story_provider_name = "offline-demo-storyteller"
            self.is_story_live = False

        # Resolve Image Provider based on configuration and availability
        pref = getattr(settings, "IMAGE_PROVIDER", "auto").lower()
        if pref == "canvas":
            self.image_provider = CanvasIllustratorImageProvider()
            self.image_provider_name = "canvas-illustrator-demo"
            self.is_image_live = False
        elif pref == "hf" and settings.HF_API_KEY:
            try:
                self.image_provider = HFInferenceImageProvider()
                self.image_provider_name = f"hf-inference ({settings.HF_IMAGE_MODEL})"
                self.is_image_live = True
            except Exception as e:
                logger.warning(f"HF provider setup failed ({e}). Defaulting to Pollinations live AI.")
                self.image_provider = PollinationsAIImageProvider()
                self.image_provider_name = "ai-live-flux (Pollinations)"
                self.is_image_live = True
        else:
            # "auto" or "pollinations": Use verified live serverless provider
            try:
                self.image_provider = PollinationsAIImageProvider()
                self.image_provider_name = "ai-live-flux (Pollinations)"
                self.is_image_live = True
            except Exception as e:
                logger.warning(f"Pollinations live AI setup failed: {e}. Using CanvasIllustrator.")
                self.image_provider = CanvasIllustratorImageProvider()
                self.image_provider_name = "canvas-illustrator-demo"
                self.is_image_live = False

    def create_comic_task(self, req: PromptRequest, db: Session) -> str:
        """Initializes comic record in database and returns comic_id."""
        comic_id = str(uuid.uuid4())[:12]
        
        words = req.prompt.strip().split()
        title = " ".join(words[:4]).title() if words else "The Adventure Begins"
        if len(title) > 60:
            title = title[:60] + "..."
            
        gen_mode = "ai_live" if (self.is_story_live and self.is_image_live) else (
            "ai_partial" if (self.is_story_live or self.is_image_live) else "demo_mode"
        )
        
        comic = Comic(
            id=comic_id,
            title=title,
            prompt=req.prompt,
            character_name=req.character_name,
            character_appearance=req.character_appearance,
            setting=req.setting,
            tone=req.tone,
            art_style=req.art_style,
            panel_count=req.panel_count,
            status="pending",
            current_stage="1. Understanding the story idea",
            stage_percent=10,
            generation_mode=gen_mode,
            story_provider=self.story_provider_name,
            image_provider=self.image_provider_name
        )
        db.add(comic)
        db.commit()
        return comic_id

    async def run_generation_pipeline(self, comic_id: str):
        """Asynchronously executes the full comic creation pipeline in background."""
        db = SessionLocal()
        try:
            comic = db.query(Comic).filter(Comic.id == comic_id).first()
            if not comic:
                logger.error(f"Comic {comic_id} not found for generation")
                return

            comic.status = "processing"
            comic.current_stage = "1. Understanding the story idea"
            comic.stage_percent = 15
            db.commit()
            await asyncio.sleep(0.3)

            # --- Stage 2: Create Panel Outline ---
            comic.current_stage = "2. Creating the panel outline"
            comic.stage_percent = 30
            db.commit()
            
            try:
                outlines = self.story_provider.generate_outline(
                    prompt=comic.prompt,
                    character_name=comic.character_name,
                    character_appearance=comic.character_appearance or "",
                    setting=comic.setting,
                    tone=comic.tone,
                    art_style=comic.art_style,
                    panel_count=comic.panel_count
                )
            except Exception as e:
                if settings.ENABLE_OFFLINE_DEMO:
                    logger.warning(f"Story outline generation failed ({e}). Falling back to DeterministicStoryProvider.")
                    self.story_provider = DeterministicStoryProvider()
                    self.story_provider_name = "offline-demo-storyteller"
                    comic.story_provider = self.story_provider_name
                    comic.generation_mode = "demo_mode"
                    db.commit()
                    outlines = self.story_provider.generate_outline(
                        prompt=comic.prompt,
                        character_name=comic.character_name,
                        character_appearance=comic.character_appearance or "",
                        setting=comic.setting,
                        tone=comic.tone,
                        art_style=comic.art_style,
                        panel_count=comic.panel_count
                    )
                else:
                    raise RuntimeError(f"Live story outline generation failed: {e}")
            await asyncio.sleep(0.3)

            # --- Stage 3: Write Narration and Dialogue ---
            comic.current_stage = "3. Writing narration and dialogue"
            comic.stage_percent = 50
            db.commit()
            
            try:
                stories = self.story_provider.generate_story(
                    outline=outlines,
                    character_name=comic.character_name,
                    setting=comic.setting,
                    tone=comic.tone
                )
            except Exception as e:
                if settings.ENABLE_OFFLINE_DEMO:
                    logger.warning(f"Story dialogue generation failed ({e}). Falling back to DeterministicStoryProvider.")
                    self.story_provider = DeterministicStoryProvider()
                    self.story_provider_name = "offline-demo-storyteller"
                    comic.story_provider = self.story_provider_name
                    comic.generation_mode = "demo_mode"
                    db.commit()
                    stories = self.story_provider.generate_story(
                        outline=outlines,
                        character_name=comic.character_name,
                        setting=comic.setting,
                        tone=comic.tone
                    )
                else:
                    raise RuntimeError(f"Live story dialogue generation failed: {e}")
            await asyncio.sleep(0.3)

            # --- Stage 4: Illustrating Panels ---
            comic.current_stage = "4. Illustrating comic panels"
            comic.stage_percent = 65
            db.commit()
            
            panel_dir = settings.PANELS_DIR / comic_id
            panel_dir.mkdir(parents=True, exist_ok=True)
            
            image_paths = []
            
            for idx, outline in enumerate(outlines):
                p_num = outline.get("panel", idx + 1)
                img_file = panel_dir / f"panel_{p_num}.jpg"
                
                # Image generation with graceful fallback
                try:
                    saved_img = self.image_provider.generate_image(
                        prompt=outline.get("image_prompt", ""),
                        output_path=str(img_file),
                        character_name=comic.character_name,
                        art_style=comic.art_style,
                        panel_number=p_num
                    )
                except Exception as e:
                    logger.warning(f"Panel {p_num} image generation failed ({e}).")
                    if settings.ENABLE_OFFLINE_DEMO:
                        # Fallback to procedural canvas engine
                        fallback_illustrator = CanvasIllustratorImageProvider()
                        saved_img = fallback_illustrator.generate_image(
                            prompt=outline.get("image_prompt", ""),
                            output_path=str(img_file),
                            character_name=comic.character_name,
                            art_style=comic.art_style,
                            panel_number=p_num
                        )
                        comic.image_provider = "canvas-illustrator-demo (fallback)"
                        comic.generation_mode = "demo_mode"
                        db.commit()
                    else:
                        raise RuntimeError(f"Live panel {p_num} image generation failed: {e}")

                image_paths.append(str(img_file))
                
                # Update progress per panel
                progress = 65 + int((idx + 1) / len(outlines) * 20)
                comic.stage_percent = progress
                db.commit()
                await asyncio.sleep(0.1)

            # --- Stage 5: Assembling and Compiling PDF ---
            comic.current_stage = "5. Assembling the final comic & compiling PDF"
            comic.stage_percent = 90
            db.commit()
            
            layout = build_comic_layout(image_paths, stories, outlines)
            
            # Persist panels into database
            for item in layout:
                p_num = item["panel"]
                panel_rec = Panel(
                    id=f"{comic_id}_p{p_num}",
                    comic_id=comic_id,
                    panel_number=p_num,
                    title=item["title"],
                    scene_description=item["scene_description"],
                    caption=item["caption"],
                    narration=item["narration"],
                    dialogue=item["dialogue"],
                    image_prompt=item["image_prompt"],
                    image_path=item["image_path"]
                )
                db.add(panel_rec)
                
            # Compile PDF
            pdf_path = save_pdf(layout, comic_title=comic.title, comic_id=comic_id)
            web_pdf = "/static/exports/" + Path(pdf_path).name
            comic.pdf_path = web_pdf
            
            comic.status = "completed"
            comic.current_stage = "Comic Complete!"
            comic.stage_percent = 100
            db.commit()

        except Exception as e:
            logger.exception(f"Error in generation pipeline for {comic_id}: {e}")
            comic = db.query(Comic).filter(Comic.id == comic_id).first()
            if comic:
                comic.status = "failed"
                comic.current_stage = "Generation failed"
                comic.error_message = str(e)
                db.commit()
        finally:
            db.close()

    def regenerate_panel(self, comic_id: str, panel_id: str, custom_prompt: str = None) -> Panel:
        """Regenerates a single panel illustration and updates the compiled PDF."""
        db = SessionLocal()
        try:
            panel = db.query(Panel).filter(Panel.comic_id == comic_id, Panel.id == panel_id).first()
            comic = db.query(Comic).filter(Comic.id == comic_id).first()
            if not panel or not comic:
                raise ValueError("Panel or Comic not found")
                
            prompt = custom_prompt or panel.image_prompt
            img_file = settings.PANELS_DIR / comic_id / f"panel_{panel.panel_number}_regen_{uuid.uuid4().hex[:6]}.jpg"
            
            try:
                self.image_provider.generate_image(
                    prompt=prompt,
                    output_path=str(img_file),
                    character_name=comic.character_name,
                    art_style=comic.art_style,
                    panel_number=panel.panel_number
                )
            except Exception as e:
                logger.warning(f"Regenerate panel with {self.image_provider_name} failed ({e}). Falling back to CanvasIllustrator.")
                fallback = CanvasIllustratorImageProvider()
                fallback.generate_image(
                    prompt=prompt,
                    output_path=str(img_file),
                    character_name=comic.character_name,
                    art_style=comic.art_style,
                    panel_number=panel.panel_number
                )
            
            web_path = f"/static/panels/{comic_id}/{img_file.name}"
            panel.image_path = web_path
            panel.is_regenerated = True
            db.commit()
            db.refresh(panel)
            
            # Recompile PDF with updated panel image
            all_panels = db.query(Panel).filter(Panel.comic_id == comic_id).order_by(Panel.panel_number).all()
            layout = []
            for p in all_panels:
                panel_file = Path(p.image_path).name
                raw_path = str(settings.PANELS_DIR / comic_id / panel_file)
                layout.append({
                    "panel": p.panel_number,
                    "title": p.title,
                    "scene_description": p.scene_description,
                    "caption": p.caption,
                    "narration": p.narration,
                    "dialogue": p.dialogue,
                    "image_prompt": p.image_prompt,
                    "image_path": p.image_path,
                    "raw_image_path": raw_path
                })
            new_pdf = save_pdf(layout, comic_title=comic.title, comic_id=comic_id)
            comic.pdf_path = "/static/exports/" + Path(new_pdf).name
            db.commit()
            db.refresh(panel)
            db.expunge(panel)
            
            return panel
        finally:
            db.close()

comic_service = ComicService()
