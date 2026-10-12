# ComicCraft — Where Imagination Becomes a Comic 🎨📖

ComicCraft is a full-stack, AI-powered web application that turns any natural language prompt into a complete, illustrated 5-panel comic book. Featuring dynamic storytelling with Google Gemini models, modular image illustration providers, real-time stage progress tracking, and professional multi-page PDF generation.

---

## ✨ Features

- **Split-Layout Comic Creation Studio**: Configure story ideas, main hero details, setting, tone, and art styles with visual cards and live metadata updates.
- **Multi-Stage AI Pipeline**:
  - `1. Understanding the story idea`
  - `2. Creating the panel outline` (via Gemini Flash / `gemini-2.5-flash`)
  - `3. Writing narration and dialogue` (via Gemini Pro / `gemini-2.5-pro`)
  - `4. Illustrating comic panels` (Hugging Face Inference, local Diffusers, or dynamic Canvas Illustrator)
  - `5. Assembling the final comic & compiling PDF`
- **Honest Fallback System**: No silent mocking. Clearly badges generated content as `✨ AI Live Generated` vs `🎭 Offline Demo Mode`.
- **Speech Bubble & Panel Reader**: Rich reading interface featuring character speech bubbles with tails, ambient caption boxes, and individual panel regenerations.
- **Publisher-Grade Multi-Page PDF**: Custom cover, styled panel headers, embedded high-resolution illustrations, dialogue boxes, and page numbering using `fpdf2`.
- **Non-Blocking Background Tasks & Persistence**: SQLite metadata storage and asynchronous background task progression via FastAPI.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (SQLite), Pydantic v2
- **AI Storytelling**: Official `google-genai` SDK (`gemini-2.5-flash`, `gemini-2.5-pro`)
- **Image Generation**: Modular provider supporting Hugging Face Inference API, local Diffusers, or dynamic PIL Canvas Illustrator
- **PDF Publishing**: `fpdf2`
- **Frontend**: HTML5, Jinja2 Templates, Vanilla CSS Design System (Comic red, electric blue, warm ivory halftone), Vanilla JavaScript

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.11)
- Git

### 2. Clone and Setup Environment

#### Windows (PowerShell / Command Prompt)
```powershell
# Create virtual environment
python -m venv comiccraft-env

# Activate virtual environment
comiccraft-env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### macOS / Linux
```bash
# Create virtual environment
python3 -m venv comiccraft-env

# Activate virtual environment
source comiccraft-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Open `.env` and configure your API keys (optional for testing in demo mode):
```ini
# Google Gemini API (Get free key from https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_FLASH_MODEL=gemini-2.5-flash
GEMINI_PRO_MODEL=gemini-2.5-pro

# Hugging Face API (Get token from https://huggingface.co/settings/tokens)
HF_API_KEY=your_huggingface_token_here
HF_IMAGE_MODEL=runwayml/stable-diffusion-v1-5

# Enable offline fallback if keys are missing
ENABLE_OFFLINE_DEMO=True
```

*Note: If no API keys are supplied, ComicCraft will seamlessly run in **Offline Demo Mode**, utilizing the built-in deterministic story generator and canvas illustrator.*

### 4. Run the Application
```bash
# Using python runner
python run.py

# Or directly with Uvicorn
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open your browser and navigate to:
- **Web Studio**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **FastAPI Interactive Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 🧪 Running Automated Tests

Run the full automated test suite with `pytest`:
```bash
python -m pytest -v
```

All 12 unit, route, schema, pipeline, and end-to-end integration tests will run without consuming external API credits.

---

## 📖 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | ComicCraft landing page |
| `GET` | `/studio` | Split-layout comic creation workspace |
| `POST` | `/generate` | Form-based comic generation (Redirects to reader) |
| `POST` | `/api/comics/generate` | JSON API comic generation |
| `GET` | `/comic/{comic_id}` | Digital comic reader with speech bubbles |
| `GET` | `/api/comics/{comic_id}/status` | Real-time generation progress and stage tracking |
| `POST` | `/api/comics/{comic_id}/panels/{panel_id}/regenerate` | Regenerate individual panel illustration |
| `GET` | `/api/comics/{comic_id}/pdf` | Direct multi-page PDF download |
| `GET` | `/test-image` | Developer utility to test image generation directly |
| `GET` | `/health` | Application health and provider status |

---

## 🎨 Architecture Overview

```
comiccraft/
├── app/
│   ├── main.py                     # FastAPI entrypoint & lifecycle
│   ├── config.py                   # Pydantic Settings & environment loader
│   ├── database.py                 # SQLite database and SQLAlchemy models
│   ├── schemas.py                  # Pydantic validation schemas
│   ├── routes.py                   # Web and API route controllers
│   ├── services/
│   │   ├── story_provider.py       # Gemini GenAI & Deterministic Storyteller
│   │   ├── image_provider.py       # HF Inference, Diffusers, and Canvas Illustrator
│   │   ├── comic_service.py        # Background task coordinator & stage tracker
│   │   ├── layout_builder.py       # Speech bubble and layout binding
│   │   └── pdf_service.py          # FPDF2 multi-page PDF publisher
│   ├── templates/                  # Jinja2 templates (index, studio, reader, export)
│   └── static/                     # CSS, JS, generated panels, and PDFs
├── tests/                          # Pytest automated test suite
├── run.py                          # Local server launcher
└── requirements.txt
```

---

## 🛡️ License
MIT License. Created for the ComicCraft Project.
