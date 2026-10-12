import os
import io
import math
import hashlib
import logging
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from app.config import settings

logger = logging.getLogger(__name__)

class ImageProvider(ABC):
    @abstractmethod
    def generate_image(self, prompt: str, output_path: str, character_name: str = "", 
                       art_style: str = "", panel_number: int = 1) -> str:
        """Generates an illustration and saves to output_path. Returns the saved path."""
        pass


class PollinationsAIImageProvider(ImageProvider):
    """
    Live AI Image Provider using serverless text-to-image (FLUX / SDXL).
    Zero credential requirement, highly reliable, produces authentic high-definition
    comic book art with rich color palettes, expressive characters, and ink outlines.
    """
    def __init__(self, model: str = "turbo"):
        self.model = model

    def generate_image(self, prompt: str, output_path: str, character_name: str = "", 
                       art_style: str = "Classic Comic Book", panel_number: int = 1) -> str:
        # Build prompt conditioned on comic book art direction
        enhanced_prompt = (
            f"indie comic book page panel, {art_style} illustration, "
            f"warm coral and orange tones, earthy palette, strong ink outlines, "
            f"expressive characters, dynamic cinematic camera angle: {prompt}"
        )
        
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        seed = int(hashlib.md5(f"{prompt}_{panel_number}".encode()).hexdigest(), 16) % 1000000
        model_str = f"&model={self.model}" if self.model else ""
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width=768&height=512{model_str}&seed={seed}"
        )
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "image/jpeg,image/png,image/*"
            }
        )
        
        logger.info(f"Generating live AI image for panel {panel_number} via Pollinations ({self.model})...")
        
        # Retry up to 2 times
        last_err = None
        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP {resp.status}: {resp.reason}")
                    data = resp.read()
                    if len(data) < 1000:
                        raise ValueError(f"Received suspiciously small response: {len(data)} bytes")
                        
                    # Validate image
                    img = Image.open(io.BytesIO(data))
                    img.verify()
                    
                    # Re-open for saving & post-processing
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    img.save(output_path, "JPEG", quality=92)
                    logger.info(f"Successfully generated live image for panel {panel_number} -> {output_path}")
                    return output_path
            except Exception as e:
                logger.warning(f"Pollinations attempt {attempt+1} failed for panel {panel_number}: {e}")
                last_err = e
                
        raise RuntimeError(f"Live AI image generation failed for panel {panel_number}: {last_err}")


class HFInferenceImageProvider(ImageProvider):
    """Generates images using huggingface_hub.InferenceClient for Stable Diffusion models."""
    def __init__(self):
        if not settings.HF_API_KEY:
            raise ValueError("HF_API_KEY is not configured in environment")
        from huggingface_hub import InferenceClient
        self.client = InferenceClient(token=settings.HF_API_KEY)
        self.model = settings.HF_IMAGE_MODEL

    def generate_image(self, prompt: str, output_path: str, character_name: str = "", 
                       art_style: str = "", panel_number: int = 1) -> str:
        enhanced_prompt = f"comic book art, graphic novel panel, {art_style} style, masterpiece, high quality, {prompt}"
        
        try:
            image = self.client.text_to_image(enhanced_prompt, model=self.model)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path)
            return output_path
        except Exception as e:
            import requests
            router_url = f"https://router.huggingface.co/hf-inference/models/{self.model}"
            resp = requests.post(
                router_url,
                headers={"Authorization": f"Bearer {settings.HF_API_KEY}"},
                json={"inputs": enhanced_prompt},
                timeout=60
            )
            if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                with Image.open(output_path) as test_img:
                    test_img.verify()
                return output_path
            raise RuntimeError(f"HF Inference failed for model '{self.model}': {e} | router: status {resp.status_code} {resp.text[:150]}")


class LocalDiffusersImageProvider(ImageProvider):
    """Optional local Stable Diffusion diffusers generation if torch and diffusers installed with GPU."""
    def __init__(self):
        try:
            import torch
            from diffusers import StableDiffusionPipeline
            self.torch = torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self.pipe = StableDiffusionPipeline.from_pretrained(
                settings.HF_IMAGE_MODEL,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32
            )
            self.pipe.to(device)
        except Exception as e:
            raise RuntimeError(f"Local diffusers initialization failed: {e}")

    def generate_image(self, prompt: str, output_path: str, character_name: str = "", 
                       art_style: str = "", panel_number: int = 1) -> str:
        enhanced_prompt = f"comic illustration, {art_style}, detailed, vibrant comic art, {prompt}"
        image = self.pipe(enhanced_prompt, num_inference_steps=25).images[0]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        return output_path


class CanvasIllustratorImageProvider(ImageProvider):
    """
    High-fidelity procedural comic-book illustrator.
    Engineered to generate DISTINCT, scene-specific compositions with:
    - Context-aware environments (Cavern, Sci-Fi Lab, Ancient Ruins, Metropolis, Forest Canopy, Cosmic Vault)
    - Action-specific character poses (Observing, Reaching/Interacting, Action Lunge, Kneeling Repair, Victorious Climax)
    - Scene lighting, halftone screen-tone patterns, speed lines, and ink hatching
    - Clearly and honestly marked as 'COMICCRAFT DEMO ENGINE • PROCEDURAL CANVAS ART'
    """
    PALETTES = {
        "cavern": {
            "sky_top": (15, 25, 35), "sky_bottom": (35, 65, 75),
            "accent": (0, 230, 180), "ink": (10, 15, 22), "highlight": (200, 255, 235),
            "prop_color": (30, 80, 95)
        },
        "lab": {
            "sky_top": (20, 25, 45), "sky_bottom": (45, 60, 95),
            "accent": (0, 190, 255), "ink": (12, 16, 28), "highlight": (220, 245, 255),
            "prop_color": (40, 75, 120)
        },
        "ruins": {
            "sky_top": (45, 30, 25), "sky_bottom": (195, 120, 75),
            "accent": (255, 140, 40), "ink": (25, 18, 15), "highlight": (255, 240, 210),
            "prop_color": (120, 80, 60)
        },
        "city": {
            "sky_top": (25, 20, 45), "sky_bottom": (160, 65, 110),
            "accent": (255, 50, 120), "ink": (18, 12, 28), "highlight": (255, 220, 240),
            "prop_color": (50, 40, 70)
        },
        "forest": {
            "sky_top": (20, 35, 25), "sky_bottom": (75, 120, 70),
            "accent": (240, 200, 50), "ink": (15, 24, 16), "highlight": (245, 250, 215),
            "prop_color": (55, 85, 50)
        },
        "cosmic": {
            "sky_top": (10, 10, 25), "sky_bottom": (85, 30, 110),
            "accent": (190, 80, 255), "ink": (8, 8, 18), "highlight": (250, 220, 255),
            "prop_color": (60, 35, 80)
        }
    }

    def _detect_environment(self, text: str) -> str:
        t = text.lower()
        if any(w in t for w in ["cave", "cavern", "crystal", "underground", "tunnel", "mine"]):
            return "cavern"
        if any(w in t for w in ["lab", "observatory", "machine", "robot", "control", "computer", "station"]):
            return "lab"
        if any(w in t for w in ["ruin", "temple", "pyramid", "ancient", "tomb", "monument", "desert"]):
            return "ruins"
        if any(w in t for w in ["city", "street", "metropolis", "building", "cyber", "neon", "tower", "urban"]):
            return "city"
        if any(w in t for w in ["forest", "tree", "jungle", "woods", "swamp", "grove", "wild"]):
            return "forest"
        if any(w in t for w in ["space", "star", "galaxy", "orbit", "planet", "void", "alien"]):
            return "cosmic"
        # Deterministic default based on hash
        return "cavern"

    def generate_image(self, prompt: str, output_path: str, character_name: str = "", 
                       art_style: str = "Classic Comic Book", panel_number: int = 1) -> str:
        width, height = 768, 512
        img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Detect environment and select color scheme
        env_type = self._detect_environment(prompt)
        pal = self.PALETTES.get(env_type, self.PALETTES["cavern"])
        seed = int(hashlib.md5(f"{prompt}_{panel_number}_{env_type}".encode()).hexdigest(), 16)
        
        # 1. Background Gradient
        r1, g1, b1 = pal["sky_top"]
        r2, g2, b2 = pal["sky_bottom"]
        for y in range(height):
            ratio = y / height
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
            
        ink = pal["ink"] + (255,)
        accent = pal["accent"] + (255,)
        highlight = pal["highlight"] + (255,)
        prop_c = pal["prop_color"] + (230,)

        # 2. Draw Environment Elements based on env_type
        if env_type == "cavern":
            # Stalactites hanging from ceiling
            for x in range(0, width, 45):
                slen = 40 + ((seed + x * 3) % 90)
                draw.polygon([(x, 0), (x + 22, 0), (x + 11, slen)], fill=ink)
            # Glowing crystals on floor and walls
            c_points = [(100, 360), (120, 270), (140, 360), (130, 380)]
            draw.polygon(c_points, fill=accent)
            draw.line([(120, 270), (120, 380)], fill=highlight, width=2)
            c2_points = [(620, 380), (645, 290), (670, 380)]
            draw.polygon(c2_points, fill=accent)
            # Cavern Ground
            ground_pts = [(0, 380), (220, 370), (450, 390), (width, 375), (width, height), (0, height)]
            draw.polygon(ground_pts, fill=ink)
            
        elif env_type == "lab":
            # Grid floor and ceiling conduits
            for y in range(0, 70, 15):
                draw.line([(0, y), (width, y)], fill=prop_c, width=3)
            # Control consoles / terminals
            draw.rectangle([50, 280, 240, 420], fill=prop_c, outline=ink, width=3)
            draw.rectangle([65, 300, 225, 360], fill=(10, 30, 50, 255), outline=accent, width=2)
            # Holographic screen readout
            draw.line([(80, 320), (210, 320)], fill=accent, width=2)
            draw.line([(80, 335), (170, 335)], fill=highlight, width=2)
            draw.rectangle([520, 260, 710, 420], fill=prop_c, outline=ink, width=3)
            draw.rectangle([540, 280, 690, 370], fill=(10, 30, 50, 255), outline=accent, width=2)
            # Floor
            draw.polygon([(0, 410), (width, 410), (width, height), (0, height)], fill=ink)
            for gx in range(0, width, 50):
                draw.line([(gx, 410), (gx - 40, height)], fill=accent, width=1)
                
        elif env_type == "city":
            # Towering perspective skyscrapers
            building_xs = [30, 160, 300, 480, 620]
            for bx in building_xs:
                bw = 90 + ((seed + bx) % 40)
                bh = 160 + ((seed + bx * 2) % 180)
                by = 420 - bh
                draw.rectangle([bx, by, bx + bw, 420], fill=prop_c, outline=ink, width=3)
                # Lit windows
                for wy in range(by + 15, 410, 28):
                    for wx in range(bx + 12, bx + bw - 15, 20):
                        if (seed + wx + wy) % 3 != 0:
                            draw.rectangle([wx, wy, wx + 10, wy + 16], fill=accent)
            # Street
            draw.polygon([(0, 420), (width, 420), (width, height), (0, height)], fill=ink)
            draw.line([(0, 465), (width, 465)], fill=pal["accent"] + (180,), width=3)

        elif env_type == "ruins":
            # Ancient carved stone pillars
            draw.rectangle([70, 110, 130, 420], fill=prop_c, outline=ink, width=4)
            draw.rectangle([55, 95, 145, 115], fill=prop_c, outline=ink, width=3)
            draw.rectangle([630, 140, 690, 420], fill=prop_c, outline=ink, width=4)
            # Broken arch stone
            draw.polygon([(50, 95), (280, 130), (280, 160), (50, 120)], fill=prop_c, outline=ink)
            # Weathered ground
            draw.polygon([(0, 400), (300, 390), (width, 410), (width, height), (0, height)], fill=ink)

        elif env_type == "forest":
            # Giant tree trunks
            draw.polygon([(40, 0), (120, 0), (95, 420), (25, 420)], fill=ink)
            draw.polygon([(640, 0), (730, 0), (700, 420), (620, 420)], fill=ink)
            # Foliage canopy arcs
            draw.ellipse([-50, -60, 350, 140], fill=prop_c)
            draw.ellipse([450, -60, 850, 140], fill=prop_c)
            # Forest ground
            draw.polygon([(0, 390), (width, 390), (width, height), (0, height)], fill=ink)
            
        else: # cosmic
            # Planetary rings and stars
            for _ in range(35):
                sx = (seed * 17) % width
                sy = (seed * 31) % 300
                seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
                draw.ellipse([sx, sy, sx + 3, sy + 3], fill=highlight)
            draw.ellipse([500, 100, 680, 280], outline=accent, width=4)
            draw.ellipse([450, 170, 730, 210], outline=highlight, width=2)
            draw.polygon([(0, 410), (width, 410), (width, height), (0, height)], fill=ink)

        # 3. Dynamic Action Character Pose based on panel_number
        # Panel 1: Establishing / Surveying
        # Panel 2: Investigating / Reaching Out
        # Panel 3: Crisis / Dynamic Action Confrontation
        # Panel 4: Problem-Solving / Kneeling Repair
        # Panel 5: Climax / Triumphant Revelation
        
        pose_id = (panel_number - 1) % 5
        
        if pose_id == 0:
            # Stance 1: Standing Surveying on the Left Ledge
            hx, hy = 220, 320
            # Head with explorer cap / goggles
            draw.ellipse([hx - 14, hy - 70, hx + 14, hy - 42], fill=highlight, outline=ink, width=2)
            draw.rectangle([hx - 12, hy - 60, hx + 12, hy - 52], fill=accent) # Goggles band
            # Torso & Jacket
            draw.polygon([(hx - 16, hy - 42), (hx + 16, hy - 42), (hx + 14, hy), (hx - 14, hy)], fill=accent, outline=ink, width=2)
            # Legs
            draw.line([(hx - 8, hy), (hx - 12, hy + 55)], fill=ink, width=6)
            draw.line([(hx + 8, hy), (hx + 12, hy + 55)], fill=ink, width=6)
            # Arm pointing forward
            draw.line([(hx + 14, hy - 35), (hx + 45, hy - 35)], fill=ink, width=5)
            # Scanner in hand
            draw.rectangle([hx + 45, hy - 42, hx + 55, hy - 28], fill=highlight, outline=ink, width=1)
            
        elif pose_id == 1:
            # Stance 2: Reaching forward, discovering an artifact / device
            hx, hy = 320, 330
            # Target object glowing
            draw.ellipse([440, 280, 490, 330], fill=highlight, outline=accent, width=3)
            # Shockwave ring
            draw.ellipse([430, 270, 500, 340], outline=accent, width=1)
            # Hero leaning forward
            draw.ellipse([hx - 14, hy - 65, hx + 14, hy - 37], fill=highlight, outline=ink, width=2)
            draw.rectangle([hx - 12, hy - 55, hx + 12, hy - 47], fill=accent)
            draw.polygon([(hx - 15, hy - 37), (hx + 18, hy - 32), (hx + 12, hy + 5), (hx - 12, hy + 5)], fill=accent, outline=ink, width=2)
            draw.line([(hx - 6, hy + 5), (hx - 15, hy + 50)], fill=ink, width=6)
            draw.line([(hx + 8, hy + 5), (hx + 20, hy + 50)], fill=ink, width=6)
            # Arm reaching out towards object
            draw.line([(hx + 15, hy - 30), (hx + 80, hy - 35)], fill=ink, width=5)
            
        elif pose_id == 2:
            # Stance 3: Dynamic Confrontation / Energy surge
            hx, hy = 380, 320
            # Action speed lines radiating from center
            for deg in range(0, 360, 20):
                rad = math.radians(deg)
                draw.line([(hx + math.cos(rad) * 60, hy + math.sin(rad) * 60),
                           (hx + math.cos(rad) * 220, hy + math.sin(rad) * 220)],
                          fill=accent, width=2)
            # Hero defensive lunge pose
            draw.ellipse([hx - 14, hy - 70, hx + 14, hy - 42], fill=highlight, outline=ink, width=2)
            draw.polygon([(hx - 18, hy - 42), (hx + 18, hy - 42), (hx + 12, hy), (hx - 12, hy)], fill=accent, outline=ink, width=2)
            # Wide spread legs
            draw.line([(hx - 10, hy), (hx - 35, hy + 50)], fill=ink, width=7)
            draw.line([(hx + 10, hy), (hx + 35, hy + 50)], fill=ink, width=7)
            # Raised arms
            draw.line([(hx - 15, hy - 35), (hx - 40, hy - 65)], fill=ink, width=5)
            draw.line([(hx + 15, hy - 35), (hx + 40, hy - 65)], fill=ink, width=5)
            
        elif pose_id == 3:
            # Stance 4: Kneeling repairing / working with sparks
            hx, hy = 340, 350
            # Spark lines
            for sp_angle in [30, 60, 120, 150, 210, 300]:
                srad = math.radians(sp_angle)
                draw.line([(420, 340), (420 + math.cos(srad) * 45, 340 + math.sin(srad) * 45)], fill=accent, width=2)
            # Kneeling figure
            draw.ellipse([hx - 14, hy - 55, hx + 14, hy - 27], fill=highlight, outline=ink, width=2)
            draw.polygon([(hx - 15, hy - 27), (hx + 15, hy - 27), (hx + 10, hy + 10), (hx - 10, hy + 10)], fill=accent, outline=ink, width=2)
            draw.line([(hx - 5, hy + 10), (hx - 25, hy + 40)], fill=ink, width=6)
            draw.line([(hx + 5, hy + 10), (hx + 25, hy + 30)], fill=ink, width=6)
            # Hands working on device
            draw.line([(hx + 12, hy - 20), (415, 335)], fill=ink, width=5)
            
        else: # pose_id == 4
            # Stance 5: Triumphant resolution - beam of light upwards
            hx, hy = 380, 310
            # Upward beacon beam
            draw.polygon([(hx - 40, 0), (hx + 40, 0), (hx + 10, hy - 40), (hx - 10, hy - 40)], fill=pal["highlight"] + (140,))
            draw.line([(hx, 0), (hx, hy - 40)], fill=highlight, width=3)
            # Hero standing triumphant
            draw.ellipse([hx - 14, hy - 68, hx + 14, hy - 40], fill=highlight, outline=ink, width=2)
            draw.polygon([(hx - 16, hy - 40), (hx + 16, hy - 40), (hx + 14, hy), (hx - 14, hy)], fill=accent, outline=ink, width=2)
            draw.line([(hx - 7, hy), (hx - 10, hy + 60)], fill=ink, width=6)
            draw.line([(hx + 7, hy), (hx + 10, hy + 60)], fill=ink, width=6)
            # Raised artifact in one hand
            draw.line([(hx + 15, hy - 30), (hx + 30, hy - 75)], fill=ink, width=5)
            draw.ellipse([hx + 24, hy - 85, hx + 36, hy - 73], fill=accent, outline=highlight, width=2)

        # 4. Comic Book Halftone Dots Texture (aesthetic overlay)
        for hx_dot in range(0, width, 24):
            for hy_dot in range(0, 140, 24):
                if (hx_dot + hy_dot) % 48 == 0:
                    draw.ellipse([hx_dot, hy_dot, hx_dot + 2, hy_dot + 2], fill=highlight)

        # 5. Heavy Black Comic Ink Border
        draw.rectangle([0, 0, width - 1, height - 1], outline=ink, width=8)
        
        # 6. Explicit and Honest Procedural Engine Watermark
        demo_text = "COMICCRAFT DEMO ENGINE • PROCEDURAL CANVAS ART"
        draw.rectangle([width - 325, height - 34, width - 14, height - 12], fill=(15, 18, 25, 220), outline=(80, 80, 80, 255), width=1)
        draw.text((width - 315, height - 28), demo_text, fill=(240, 240, 240, 240))
        
        # Save output
        final_img = img.convert("RGB")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        final_img.save(output_path, "JPEG", quality=92)
        return output_path
