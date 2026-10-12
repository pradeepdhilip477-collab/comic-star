import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("comiccraft")

# Initialize database tables
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ComicCraft — AI Comic Story Creator using Gemini Models & Modular Illustrators"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include routes
app.include_router(router)

@app.on_event("startup")
async def on_startup():
    logger.info(f"🚀 {settings.APP_NAME} started successfully!")
    logger.info(f"Gemini API Configured: {bool(settings.GEMINI_API_KEY)}")
    logger.info(f"HuggingFace API Configured: {bool(settings.HF_API_KEY)}")
