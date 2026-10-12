import os
import logging
from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, Comic, Panel
from app.schemas import PromptRequest, ComicDetailSchema, ComicStatusResponse, RegeneratePanelRequest
from app.services.comic_service import comic_service

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# --- Page Routes ---

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Landing Page showcasing ComicCraft, hero art, recent creations, and workflow."""
    recent_comics = db.query(Comic).filter(Comic.status == "completed").order_by(Comic.created_at.desc()).limit(6).all()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "recent_comics": recent_comics,
            "story_provider": comic_service.story_provider_name,
            "image_provider": comic_service.image_provider_name,
            "is_ai_live": comic_service.is_story_live
        }
    )

@router.get("/studio", response_class=HTMLResponse)
async def studio(request: Request):
    """Comic Creation Workspace with Split-Layout and interactive style/tone pickers."""
    return templates.TemplateResponse(
        request=request,
        name="studio.html",
        context={
            "story_provider": comic_service.story_provider_name,
            "image_provider": comic_service.image_provider_name,
            "is_ai_live": comic_service.is_story_live
        }
    )

@router.post("/generate", response_class=HTMLResponse)
async def generate_comic_form(
    request: Request,
    background_tasks: BackgroundTasks,
    prompt: str = Form(...),
    character_name: str = Form(...),
    character_appearance: str = Form(None),
    setting: str = Form("Modern City"),
    tone: str = Form("Adventure"),
    style: str = Form("Classic Comic Book"),
    panel_count: int = Form(5),
    db: Session = Depends(get_db)
):
    """
    HTML Form submission handler. Validates inputs, creates task,
    and returns immediate response redirecting to viewer/status.
    """
    try:
        req = PromptRequest(
            prompt=prompt,
            character_name=character_name,
            character_appearance=character_appearance,
            setting=setting,
            tone=tone,
            art_style=style,
            panel_count=panel_count
        )
        comic_id = comic_service.create_comic_task(req, db)
        background_tasks.add_task(comic_service.run_generation_pipeline, comic_id)
        return RedirectResponse(url=f"/comic/{comic_id}", status_code=303)
    except Exception as e:
        logger.exception("Form comic generation error")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/comic/{comic_id}", response_class=HTMLResponse)
async def view_comic(comic_id: str, request: Request, db: Session = Depends(get_db)):
    """Displays the comic reading experience, speech bubbles, status tracker, and PDF download."""
    comic = db.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
        
    panels = db.query(Panel).filter(Panel.comic_id == comic_id).order_by(Panel.panel_number).all()
    
    return templates.TemplateResponse(
        request=request,
        name="comic_preview.html",
        context={
            "comic": comic,
            "panels": panels,
            "pdf_path": comic.pdf_path
        }
    )

@router.get("/export-success", response_class=HTMLResponse)
async def export_success(request: Request, pdf_path: str = "", comic_title: str = "My Comic"):
    """Export Confirmation Page."""
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={
            "pdf_path": pdf_path,
            "comic_title": comic_title
        }
    )

# --- JSON API Routes ---

@router.post("/api/comics/generate", response_model=dict)
async def api_generate_comic(
    req: PromptRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """JSON API route to trigger comic generation."""
    comic_id = comic_service.create_comic_task(req, db)
    background_tasks.add_task(comic_service.run_generation_pipeline, comic_id)
    return {
        "comic_id": comic_id,
        "status": "processing",
        "status_url": f"/api/comics/{comic_id}/status",
        "view_url": f"/comic/{comic_id}"
    }

@router.post("/generate-comic/json")
async def generate_comic_json_spec(
    req: PromptRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Specification route: /generate-comic/json"""
    comic_id = comic_service.create_comic_task(req, db)
    background_tasks.add_task(comic_service.run_generation_pipeline, comic_id)
    return {
        "comic_id": comic_id,
        "status": "processing",
        "redirect_url": f"/comic/{comic_id}"
    }

@router.get("/api/comics/{comic_id}/status", response_model=ComicStatusResponse)
async def get_comic_status(comic_id: str, db: Session = Depends(get_db)):
    """Exposes real status, stage information, and progress percent."""
    comic = db.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
        
    panel_count = db.query(Panel).filter(Panel.comic_id == comic_id).count()
    return ComicStatusResponse(
        id=comic.id,
        status=comic.status,
        current_stage=comic.current_stage or "",
        stage_percent=comic.stage_percent or 0,
        error_message=comic.error_message,
        generation_mode=comic.generation_mode,
        panel_count=comic.panel_count,
        panels_ready=panel_count,
        pdf_ready=bool(comic.pdf_path),
        redirect_url=f"/comic/{comic.id}"
    )

@router.get("/api/comics/{comic_id}", response_model=ComicDetailSchema)
async def get_comic_data(comic_id: str, db: Session = Depends(get_db)):
    """Returns complete JSON structure of a comic and its panels."""
    comic = db.query(Comic).filter(Comic.id == comic_id).first()
    if not comic:
        raise HTTPException(status_code=404, detail="Comic not found")
    return comic

@router.post("/api/comics/{comic_id}/panels/{panel_id}/regenerate")
async def regenerate_panel_api(
    comic_id: str, 
    panel_id: str, 
    body: RegeneratePanelRequest = RegeneratePanelRequest(),
    db: Session = Depends(get_db)
):
    """Regenerates a single panel illustration."""
    try:
        updated_panel = comic_service.regenerate_panel(comic_id, panel_id, body.custom_prompt)
        return {
            "success": True,
            "panel_id": updated_panel.id,
            "new_image_path": updated_panel.image_path
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/comics/{comic_id}/pdf")
async def download_comic_pdf(comic_id: str, db: Session = Depends(get_db)):
    """Directly serves or triggers download of the compiled PDF."""
    comic = db.query(Comic).filter(Comic.id == comic_id).first()
    if not comic or not comic.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found or not compiled yet")
        
    pdf_filename = Path(comic.pdf_path).name
    file_path = settings.EXPORTS_DIR / pdf_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file missing from disk")
        
    return FileResponse(
        path=str(file_path),
        filename=f"{comic.title.replace(' ', '_')}.pdf",
        media_type="application/pdf"
    )

@router.get("/test-image")
async def test_image_route(prompt: str = "A futuristic city at sunset, sci-fi, cinematic, artstation"):
    """Developer test endpoint to test image generation directly."""
    try:
        img_file = settings.PANELS_DIR / "test_image.jpg"
        try:
            saved = comic_service.image_provider.generate_image(prompt, str(img_file))
            provider_used = comic_service.image_provider_name
        except Exception as e:
            if settings.ENABLE_OFFLINE_DEMO:
                from app.services.image_provider import CanvasIllustratorImageProvider
                fallback_provider = CanvasIllustratorImageProvider()
                saved = fallback_provider.generate_image(prompt, str(img_file))
                provider_used = "canvas-illustrator-demo"
            else:
                raise
        return {
            "status": "success",
            "message": "Image generated successfully",
            "provider": provider_used,
            "path": f"/static/panels/test_image.jpg"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check route."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "story_provider": comic_service.story_provider_name,
        "image_provider": comic_service.image_provider_name,
        "gemini_api_configured": bool(settings.GEMINI_API_KEY),
        "hf_api_configured": bool(settings.HF_API_KEY)
    }
