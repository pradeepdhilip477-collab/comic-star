from typing import List, Dict, Any

def build_comic_layout(image_paths: List[str], stories: List[Dict[str, Any]], outlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Organizes the generated images, story narration, captions, and outlines into a structured layout.
    Matches each image with its corresponding panel data.
    """
    layout = []
    
    # Create indexed lookup for outlines and stories
    story_map = {s.get("panel", idx + 1): s for idx, s in enumerate(stories)}
    outline_map = {o.get("panel", idx + 1): o for idx, o in enumerate(outlines)}
    
    total = max(len(image_paths), len(outlines))
    for idx in range(1, total + 1):
        outline = outline_map.get(idx, {})
        story = story_map.get(idx, {})
        img_path = image_paths[idx - 1] if idx - 1 < len(image_paths) else ""
        
        # Format web-accessible image path
        web_img = img_path
        if "/app/static/" in img_path.replace("\\", "/"):
            web_img = "/static/" + img_path.replace("\\", "/").split("/app/static/")[1]
        elif "static/" in img_path.replace("\\", "/"):
            web_img = "/" + img_path.replace("\\", "/").split("static/")[0] + "static/" + img_path.replace("\\", "/").split("static/")[1]
            if not web_img.startswith("/static/"):
                web_img = "/static/" + img_path.replace("\\", "/").split("static/")[1]
        
        layout.append({
            "panel": idx,
            "title": outline.get("title", f"Panel {idx}"),
            "scene_description": outline.get("scene_description", ""),
            "main_character_action": outline.get("main_character_action", ""),
            "caption": story.get("caption", ""),
            "narration": story.get("narration", ""),
            "dialogue": story.get("dialogue", ""),
            "image_prompt": outline.get("image_prompt", ""),
            "image_path": web_img,
            "raw_image_path": img_path
        })
        
    return layout
