# services/image_generation.py
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Constants for image generation
FONT_DIR = "assets/fonts"
IMAGE_DIR = "assets/backgrounds"
CARD_WIDTH = 800
CARD_HEIGHT = 400
COLORS = {
    "background": (245, 245, 245),
    "text_primary": (50, 50, 50),
    "text_secondary": (100, 100, 100),
    "accent": (65, 105, 225),  # Royal Blue
    "border": (220, 220, 220),
    "shadow": (200, 200, 200),
}

# Create directories if they don't exist
os.makedirs(FONT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# Default font paths - users will need to add actual font files to these locations
DEFAULT_FONT_PATHS = {
    "regular": os.path.join(FONT_DIR, "OpenSans-Regular.ttf"),
    "bold": os.path.join(FONT_DIR, "OpenSans-Bold.ttf"),
    "italic": os.path.join(FONT_DIR, "OpenSans-Italic.ttf"),
}

def get_font(font_type: str = "regular", size: int = 24) -> Optional[ImageFont.FreeTypeFont]:
    """Get a font for image generation, with fallback to default."""
    font_path = DEFAULT_FONT_PATHS.get(font_type)
    
    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        else:
            # Fallback to default font
            return ImageFont.load_default()
    except Exception as e:
        logger.error(f"Error loading font: {e}")
        return ImageFont.load_default()

def create_word_card(word: str, translation: str, 
                    transcription: Optional[str] = None,
                    example: Optional[str] = None,
                    level: Optional[str] = None) -> str:
    """
    Create a visually appealing image card for a vocabulary word.
    
    Args:
        word: The English word
        translation: The translation of the word
        transcription: Optional phonetic transcription
        example: Optional example usage
        level: Optional level indicator (A1, B2, etc.)
        
    Returns:
        Path to the generated image file
    """
    try:
        # Create image with white background
        img = Image.new('RGB', (CARD_WIDTH, CARD_HEIGHT), COLORS["background"])
        draw = ImageDraw.Draw(img)
        
        # Get fonts
        word_font = get_font("bold", 48)
        translation_font = get_font("bold", 36)
        transcription_font = get_font("italic", 24)
        example_font = get_font("regular", 24)
        level_font = get_font("bold", 20)
        
        # Draw border with slight shadow effect
        draw.rectangle([(10, 10), (CARD_WIDTH-10, CARD_HEIGHT-10)], 
                      outline=COLORS["border"], width=2)
        
        # Draw word and translation
        draw.text((CARD_WIDTH//2, 80), word, font=word_font, 
                 fill=COLORS["text_primary"], anchor="mm")
        
        draw.text((CARD_WIDTH//2, 150), translation, font=translation_font, 
                 fill=COLORS["accent"], anchor="mm")
        
        # Draw transcription if provided
        if transcription:
            draw.text((CARD_WIDTH//2, 200), f"[{transcription}]", 
                     font=transcription_font, fill=COLORS["text_secondary"], 
                     anchor="mm")
            
        # Draw example if provided
        if example:
            # Limit example length for display
            if len(example) > 60:
                example = example[:57] + "..."
                
            draw.text((CARD_WIDTH//2, 260), f'"{example}"', 
                     font=example_font, fill=COLORS["text_secondary"], 
                     anchor="mm")
        
        # Draw level indicator if provided
        if level:
            draw.text((CARD_WIDTH-30, 30), level, font=level_font, 
                     fill=COLORS["accent"], anchor="mm")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            file_path = temp_file.name
            img.save(file_path, "PNG")
            
        return file_path
        
    except Exception as e:
        logger.error(f"Error creating word card: {e}")
        return ""

def create_progress_chart(learned_count: int, target_count: int = None, 
                         days_active: int = None) -> str:
    """
    Create a progress chart showing the user's learning progress.
    
    Args:
        learned_count: Number of words learned
        target_count: Optional target number of words
        days_active: Optional number of days the user has been active
        
    Returns:
        Path to the generated image file
    """
    try:
        # Create image with white background
        img = Image.new('RGB', (800, 400), COLORS["background"])
        draw = ImageDraw.Draw(img)
        
        # Get fonts
        title_font = get_font("bold", 36)
        label_font = get_font("regular", 24)
        number_font = get_font("bold", 48)
        
        # Draw title
        draw.text((400, 50), "Learning Progress", font=title_font, 
                 fill=COLORS["text_primary"], anchor="mm")
        
        # Draw learned words count in a circle
        circle_center = (200, 200)
        circle_radius = 100
        draw.ellipse((circle_center[0]-circle_radius, circle_center[1]-circle_radius,
                     circle_center[0]+circle_radius, circle_center[1]+circle_radius),
                    outline=COLORS["accent"], width=3)
        
        draw.text((circle_center[0], circle_center[1]-20), "Words Learned", 
                 font=label_font, fill=COLORS["text_secondary"], anchor="mm")
        
        draw.text((circle_center[0], circle_center[1]+20), str(learned_count), 
                 font=number_font, fill=COLORS["accent"], anchor="mm")
        
        # Draw additional stats if provided
        if target_count:
            draw.text((600, 150), "Target", font=label_font, 
                     fill=COLORS["text_secondary"], anchor="mm")
            draw.text((600, 190), str(target_count), font=number_font, 
                     fill=COLORS["text_primary"], anchor="mm")
            
            # Draw progress bar
            progress = min(1.0, learned_count / target_count) if target_count > 0 else 0
            bar_width = 300
            bar_height = 30
            bar_left = 450
            bar_top = 250
            
            # Draw bar background
            draw.rectangle([(bar_left, bar_top), 
                           (bar_left + bar_width, bar_top + bar_height)], 
                          fill=COLORS["border"])
            
            # Draw progress fill
            draw.rectangle([(bar_left, bar_top), 
                           (bar_left + int(bar_width * progress), bar_top + bar_height)], 
                          fill=COLORS["accent"])
            
            # Draw percentage
            draw.text((bar_left + bar_width//2, bar_top + bar_height//2), 
                     f"{int(progress*100)}%", font=label_font, 
                     fill=COLORS["text_primary"], anchor="mm")
        
        if days_active:
            draw.text((600, 300), "Days Active", font=label_font, 
                     fill=COLORS["text_secondary"], anchor="mm")
            draw.text((600, 340), str(days_active), font=number_font, 
                     fill=COLORS["text_primary"], anchor="mm")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            file_path = temp_file.name
            img.save(file_path, "PNG")
            
        return file_path
        
    except Exception as e:
        logger.error(f"Error creating progress chart: {e}")
        return ""

def create_level_badge(level: str) -> str:
    """
    Create a badge image for the user's current level.
    
    Args:
        level: The user's level (A1, A2, B1, etc.)
        
    Returns:
        Path to the generated image file
    """
    try:
        # Create a circular badge
        size = 200
        img = Image.new('RGB', (size, size), COLORS["background"])
        draw = ImageDraw.Draw(img)
        
        # Draw circular background
        circle_color = {
            "A1": (152, 251, 152),  # Pale Green
            "A2": (144, 238, 144),  # Light Green
            "B1": (135, 206, 250),  # Light Sky Blue
            "B2": (100, 149, 237),  # Cornflower Blue
            "C1": (221, 160, 221),  # Plum
            "C2": (186, 85, 211),   # Medium Orchid
        }.get(level, COLORS["accent"])
        
        draw.ellipse((10, 10, size-10, size-10), fill=circle_color, outline=(255,255,255), width=3)
        
        # Draw level text
        level_font = get_font("bold", 80)
        draw.text((size//2, size//2), level, font=level_font, 
                 fill=(255,255,255), anchor="mm")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            file_path = temp_file.name
            img.save(file_path, "PNG")
            
        return file_path
        
    except Exception as e:
        logger.error(f"Error creating level badge: {e}")
        return ""