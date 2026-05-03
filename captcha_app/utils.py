# captcha_app/utils.py
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def generate_random_string(length=6):
    # Exclude confusing characters like 0, O, 1, l, I
    characters = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
    return ''.join(random.choice(characters) for _ in range(length))

def generate_captcha_image(text):
    # Image dimensions
    width, height = 160, 60
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Try to load a system font, fallback to default if not found
    try:
        # Note: You may need to provide a path to an actual .ttf file on your system
        # e.g., 'arial.ttf' on Windows or '/Library/Fonts/Arial.ttf' on Mac
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()

    # Draw text with slight random positioning
    for i, char in enumerate(text):
        x = 20 + (i * 20) + random.randint(-5, 5)
        y = random.randint(5, 15)
        draw.text((x, y), char, font=font, fill=(0, 0, 0))

    # Add Noise: Draw random lines
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill=(50, 50, 50), width=2)

    # Add Noise: Draw random dots
    for _ in range(100):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(100, 100, 100))

    # Save image to a BytesIO object
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()