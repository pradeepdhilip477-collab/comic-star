import os
import re
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from app.config import settings

def clean_text(text: str) -> str:
    """Sanitize text for standard latin-1 PDF rendering with clean comic punctuation."""
    if not text:
        return ""
    # Strip markdown emphasis
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    
    # Replace common typographic unicode with standard ASCII
    replacements = {
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "--",
        "\u2026": "...", "\u2022": "-",
        "\u00a0": " "
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
        
    return text.encode("latin-1", "replace").decode("latin-1")


class ComicPDF(FPDF):
    def __init__(self, comic_title="ComicCraft Story"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.comic_title = comic_title
        self.set_auto_page_break(auto=False)
        self.is_cover = True
        
    def header(self):
        if self.page_no() <= 1:
            return
        # Sleek Comic Running Header
        self.set_fill_color(26, 26, 26)
        self.rect(0, 0, 210, 13, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(255, 255, 255)
        self.set_xy(15, 2.5)
        safe_title = clean_text(self.comic_title).upper()
        self.cell(100, 8, f"COMICCRAFT  |  {safe_title}", align="L")
        self.set_xy(125, 2.5)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(200, 200, 200)
        self.cell(70, 8, "COLLECTOR'S EDITION", align="R")

    def footer(self):
        if self.page_no() <= 1:
            return
        self.set_y(-12)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"-- PAGE {self.page_no()}  *  COMICCRAFT STUDIO --", align="C")


def get_fitted_panel_image(img_path: str, target_w: float, target_h: float, panel_num: int) -> str:
    """Crops an image centered to match target aspect ratio exactly without distortion."""
    if not img_path or not os.path.exists(img_path):
        return img_path
    try:
        from PIL import Image
        with Image.open(img_path) as im:
            orig_w, orig_h = im.size
            target_ratio = target_w / target_h
            orig_ratio = orig_w / orig_h
            
            if abs(target_ratio - orig_ratio) < 0.05:
                return img_path
                
            if orig_ratio > target_ratio:
                new_w = int(orig_h * target_ratio)
                left = (orig_w - new_w) // 2
                crop_box = (left, 0, left + new_w, orig_h)
            else:
                new_h = int(orig_w / target_ratio)
                top = (orig_h - new_h) // 2
                crop_box = (0, top, orig_w, top + new_h)
                
            cropped = im.crop(crop_box)
            fitted_path = str(Path(img_path).parent / f"p{panel_num}_fit_{int(target_w)}x{int(target_h)}.jpg")
            cropped.save(fitted_path, "JPEG", quality=95)
            return fitted_path
    except Exception as e:
        return img_path


def render_panel(pdf: ComicPDF, item: dict, x: float, y: float, w: float, h: float, panel_num: int):
    """
    Renders an individual comic panel inside the page grid:
    - High-res artwork cropped without distortion
    - Heavy ink border (1.2mm)
    - Panel number badge
    - Ambient narration/caption box (upper portion)
    - Dialogue speech bubble with pointer tail (lower portion)
    """
    raw_path = item.get("raw_image_path", "")
    img_path = get_fitted_panel_image(raw_path, w, h, panel_num)
    
    # 1. Background Fill & Image
    pdf.set_fill_color(245, 243, 238)
    pdf.rect(x, y, w, h, "F")
    
    if img_path and os.path.exists(img_path):
        try:
            pdf.image(img_path, x=x, y=y, w=w, h=h)
        except Exception:
            pdf.set_xy(x + 5, y + h / 2 - 5)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(w - 10, 10, "[Illustration Loading]", align="C")
            
    # 2. Panel Number Corner Badge
    pdf.set_fill_color(26, 26, 26)
    badge_w, badge_h = 24, 7
    pdf.rect(x, y, badge_w, badge_h, "F")
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(x, y + 0.5)
    pdf.cell(badge_w, 6, f"PANEL {panel_num}", align="C")

    # 3. Ambient Narration / Caption Box (Upper area of panel)
    caption_text = clean_text(item.get("caption") or item.get("narration") or "")
    if caption_text:
        # Cap caption length so it doesn't obscure the art
        if len(caption_text) > 130:
            caption_text = caption_text[:127] + "..."
            
        c_box_w = min(w - 32, 115)
        c_box_x = x + badge_w + 3
        c_box_y = y + 2
        
        pdf.set_fill_color(255, 252, 235)  # Vintage pale yellow parchment
        pdf.set_draw_color(40, 35, 25)
        pdf.set_line_width(0.35)
        
        # Calculate height needed
        pdf.set_font("Helvetica", "I", 7.5)
        text_lines = pdf.multi_cell(c_box_w - 4, 3.8, caption_text, dry_run=True, output="LINES")
        c_box_h = max(7, len(text_lines) * 3.8 + 3)
        
        pdf.rect(c_box_x, c_box_y, c_box_w, c_box_h, "FD")
        pdf.set_xy(c_box_x + 2, c_box_y + 1.5)
        pdf.set_text_color(35, 30, 20)
        pdf.multi_cell(c_box_w - 4, 3.8, caption_text, align="L")

    # 4. Dialogue Speech Bubble with Tail (Lower area of panel)
    dialogue_raw = clean_text(item.get("dialogue", ""))
    if dialogue_raw:
        # Parse speaker and spoken text
        speaker = ""
        quote = dialogue_raw
        if ":" in dialogue_raw:
            parts = dialogue_raw.split(":", 1)
            speaker = parts[0].strip()
            quote = parts[1].strip().strip("'\"")
        elif "—" in dialogue_raw:
            parts = dialogue_raw.split("—", 1)
            speaker = parts[0].strip()
            quote = parts[1].strip().strip("'\"")
            
        if len(quote) > 120:
            quote = quote[:117] + "..."
            
        b_w = min(w - 18, 110)
        # Position in bottom-left or bottom-right
        b_x = x + 8
        b_h = 16
        
        pdf.set_font("Helvetica", "B", 7.5)
        quote_lines = pdf.multi_cell(b_w - 6, 3.8, quote, dry_run=True, output="LINES")
        b_h = max(13, len(quote_lines) * 3.8 + (6 if speaker else 4))
        
        b_y = y + h - b_h - 7  # Leave room for bubble tail
        if b_y < y + 16:
            b_y = y + 16
            
        # Draw Speech Bubble Body (White fill, crisp black ink border)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_draw_color(26, 26, 26)
        pdf.set_line_width(0.5)
        pdf.rect(b_x, b_y, b_w, b_h, "FD")
        
        # Draw Speech Bubble Tail (Pointing down-left toward speaker)
        tail_tip_x = b_x + 12
        tail_tip_y = b_y + b_h + 5
        tail_pts = [(b_x + 8, b_y + b_h), (b_x + 20, b_y + b_h), (tail_tip_x, tail_tip_y)]
        pdf.polygon(tail_pts, style="FD")
        
        # Render Speaker Name & Spoken Quote
        curr_y = b_y + 1.8
        if speaker:
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(0, 102, 204)  # Comic electric blue speaker header
            pdf.set_xy(b_x + 3, curr_y)
            pdf.cell(b_w - 6, 4, speaker.upper(), align="L")
            curr_y += 4.2
            
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(20, 20, 20)
        pdf.set_xy(b_x + 3, curr_y)
        pdf.multi_cell(b_w - 6, 3.8, f'"{quote}"', align="L")

    # 5. Heavy Outer Black Comic Ink Border (drawn last to frame cleanly)
    pdf.set_draw_color(26, 26, 26)
    pdf.set_line_width(1.2)
    pdf.rect(x, y, w, h)


def save_pdf(layout: list, comic_title: str = "ComicCraft Story", comic_id: str = "comic") -> str:
    """
    Compiles full comic layout into an authentic multi-panel graphic novel PDF.
    - Page 1: Deluxe Collector Cover
    - Pages 2+: Dynamic multi-panel layouts (2 to 3 panels per page with gutters)
    """
    pdf = ComicPDF(comic_title=comic_title)
    
    # =========================================================================
    # PAGE 1: DELUXE COMIC BOOK COVER
    # =========================================================================
    pdf.is_cover = True
    pdf.add_page()
    
    # Warm ivory vintage paper background
    pdf.set_fill_color(251, 249, 245)
    pdf.rect(0, 0, 210, 297, "F")
    
    # Outer decorative frame
    pdf.set_draw_color(26, 26, 26)
    pdf.set_line_width(1.8)
    pdf.rect(10, 12, 190, 273)
    pdf.set_line_width(0.5)
    pdf.rect(12, 14, 186, 269)
    
    # Top Comic Header Banner
    pdf.set_fill_color(255, 59, 48)  # Comic red
    pdf.rect(14, 16, 182, 28, "F")
    pdf.set_draw_color(26, 26, 26)
    pdf.set_line_width(1.2)
    pdf.rect(14, 16, 182, 28)
    
    # Issue Badge in top corner
    pdf.set_fill_color(255, 204, 0) # Gold accent
    pdf.rect(16, 18, 36, 8, "FD")
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(26, 26, 26)
    pdf.set_xy(16, 19)
    pdf.cell(36, 6, "ISSUE #1 * SPECIAL", align="C")
    
    # ComicCraft Main Masthead Wordmark
    pdf.set_xy(14, 25)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(182, 12, "COMICCRAFT", align="C")
    
    # Title Display Card
    pdf.set_y(48)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(26, 26, 26)
    safe_title = clean_text(comic_title)
    pdf.cell(0, 10, safe_title, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "Where Imagination Becomes a Comic", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    
    # Cover Artwork (Full featured panel or hero shot)
    cover_img = layout[0].get("raw_image_path") if layout else None
    cover_y = 68
    cover_w, cover_h = 170, 140
    cover_x = (210 - cover_w) / 2
    
    if cover_img and os.path.exists(cover_img):
        try:
            pdf.image(cover_img, x=cover_x, y=cover_y, w=cover_w, h=cover_h)
            # Heavy frame around cover artwork
            pdf.set_draw_color(26, 26, 26)
            pdf.set_line_width(1.5)
            pdf.rect(cover_x, cover_y, cover_w, cover_h)
        except Exception:
            pdf.rect(cover_x, cover_y, cover_w, cover_h, "D")
    else:
        pdf.rect(cover_x, cover_y, cover_w, cover_h, "D")
        
    # Bottom Teaser Bar
    pdf.set_fill_color(26, 26, 26)
    pdf.rect(14, 218, 182, 14, "F")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(255, 204, 0)
    pdf.set_xy(14, 221)
    pdf.cell(182, 8, f"FEATURING {len(layout)} FULL-COLOR ILLUSTRATED PANELS", align="C")
    
    # Metadata Footer
    pdf.set_y(242)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    date_str = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 6, f"Published on: {date_str}   |   Original Graphic Novel Edition", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.cell(0, 5, "Created with ComicCraft AI Studio", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # =========================================================================
    # PAGES 2+: MULTI-PANEL COMIC GRIDS
    # =========================================================================
    pdf.is_cover = False
    
    total_panels = len(layout)
    current_idx = 0
    
    while current_idx < total_panels:
        pdf.add_page()
        
        # Ivory background
        pdf.set_fill_color(251, 249, 245)
        pdf.rect(0, 0, 210, 297, "F")
        
        remaining = total_panels - current_idx
        
        # Determine panel layout for this page
        # If 3 or more remaining, use 3-panel dynamic layout (1 top wide, 2 bottom split)
        # If exactly 2 remaining, use 2-panel stacked layout (2 large wide panels)
        # If 1 remaining, use 1 full-page spotlight panel
        
        if remaining >= 3:
            # 3 Panels on this page
            p1 = layout[current_idx]
            p2 = layout[current_idx + 1]
            p3 = layout[current_idx + 2]
            
            # Panel 1: Top full-width establishing panel
            render_panel(pdf, p1, x=15, y=20, w=180, h=108, panel_num=p1.get("panel", current_idx + 1))
            
            # Panel 2: Bottom-Left panel
            render_panel(pdf, p2, x=15, y=136, w=86, h=128, panel_num=p2.get("panel", current_idx + 2))
            
            # Panel 3: Bottom-Right panel
            render_panel(pdf, p3, x=109, y=136, w=86, h=128, panel_num=p3.get("panel", current_idx + 3))
            
            current_idx += 3
            
        elif remaining == 2:
            # 2 Panels on this page (Stacked Wide Action Format)
            p1 = layout[current_idx]
            p2 = layout[current_idx + 1]
            
            # Top Panel
            render_panel(pdf, p1, x=15, y=20, w=180, h=118, panel_num=p1.get("panel", current_idx + 1))
            
            # Bottom Panel
            render_panel(pdf, p2, x=15, y=146, w=180, h=118, panel_num=p2.get("panel", current_idx + 2))
            
            current_idx += 2
            
        else:
            # 1 Panel Remaining (Climactic Splash Format)
            p1 = layout[current_idx]
            render_panel(pdf, p1, x=15, y=20, w=180, h=240, panel_num=p1.get("panel", current_idx + 1))
            current_idx += 1

    # Output file
    output_filename = f"comic_{comic_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = settings.EXPORTS_DIR / output_filename
    pdf.output(str(output_path))
    return str(output_path)
