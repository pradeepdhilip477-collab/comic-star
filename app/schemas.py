from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class PromptRequest(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=1500, description="The main story idea")
    character_name: str = Field(..., min_length=1, max_length=100, description="Name of the main character")
    character_appearance: Optional[str] = Field(None, max_length=500, description="Appearance details for character visual consistency")
    setting: str = Field("Modern City", max_length=100, description="Setting/Location")
    tone: str = Field("Adventure", max_length=100, description="Tone of the story")
    art_style: str = Field("Classic Comic Book", max_length=100, description="Art style")
    panel_count: int = Field(5, ge=3, le=8, description="Number of panels to generate")
    additional_notes: Optional[str] = Field(None, max_length=500, description="Custom guidelines or nuances")

class PanelOutlineSchema(BaseModel):
    panel: int
    title: str
    scene_description: str
    main_character_action: Optional[str] = None
    image_prompt: str
    narrative_purpose: Optional[str] = None

class PanelStorySchema(BaseModel):
    panel: int
    caption: Optional[str] = None
    narration: Optional[str] = None
    dialogue: Optional[str] = None

class PanelDetailSchema(BaseModel):
    id: str
    panel_number: int
    title: str
    scene_description: Optional[str] = None
    caption: Optional[str] = None
    narration: Optional[str] = None
    dialogue: Optional[str] = None
    image_prompt: str
    image_path: Optional[str] = None
    is_regenerated: bool = False

    model_config = ConfigDict(from_attributes=True)

class ComicDetailSchema(BaseModel):
    id: str
    title: str
    prompt: str
    character_name: str
    character_appearance: Optional[str] = None
    setting: str
    tone: str
    art_style: str
    panel_count: int
    status: str
    current_stage: str
    stage_percent: int
    error_message: Optional[str] = None
    generation_mode: str
    story_provider: str
    image_provider: str
    pdf_path: Optional[str] = None
    created_at: datetime
    panels: List[PanelDetailSchema] = []

    model_config = ConfigDict(from_attributes=True)

class ComicStatusResponse(BaseModel):
    id: str
    status: str
    current_stage: str
    stage_percent: int
    error_message: Optional[str] = None
    generation_mode: str
    panel_count: int
    panels_ready: int
    pdf_ready: bool
    redirect_url: Optional[str] = None

class RegeneratePanelRequest(BaseModel):
    custom_prompt: Optional[str] = None
    style_override: Optional[str] = None
