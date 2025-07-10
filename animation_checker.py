from PIL import Image
from io import BytesIO
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def encode_image_as_bytes(image_path):
    with Image.open(image_path) as img:
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-2.0-flash")


def analyze_video_frames(frame_paths):
    model = setup_gemini()

    # Construct parts: prompt + 10 images
    parts = [{
        "text": (
            "You will be shown 10 sampled frames from a video. "
            "Based on these frames, determine whether the **video is animated** (cartoon, 2D/3D animation, anime, motion graphics) "
            "or **live-action** (real people, camera footage). "
            "Please respond with only 'True' if the video is animated, or 'False' if it is live-action.\n\n"
            "Here are the frames:"
        )
    }]

    for frame_path in frame_paths:
        image_bytes = encode_image_as_bytes(frame_path)
        parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": image_bytes
            }
        })

    response = model.generate_content([{"parts": parts}])
    return response.text.strip()