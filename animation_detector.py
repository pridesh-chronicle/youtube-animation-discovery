import os
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_animated(video_url, save_videos=False, save_frames=False):
    """
    Determine if a YouTube video is animated or live-action using Gemini AI.
    
    Args:
        video_url (str): YouTube video URL
        save_videos (bool): Ignored (no longer used, kept for compatibility)
        save_frames (bool): Ignored (no longer used, kept for compatibility)
        
    Returns:
        bool: True if animated, False if live-action
    """
    try:
        # Get Gemini API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            return False
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        logger.info(f"Processing video with Gemini: {video_url}")
        
        # Create prompt for Gemini
        prompt = f"""
        Please analyze this YouTube video and classify it as either ANIMATED or LIVE-ACTION.
        YouTube URL: {video_url}
        Definitions:
        - ANIMATED content:
            - Any content primarily made up of visuals that are **artistically created rather than filmed from the real world**.
            - Includes but is not limited to:
            - 2D animation (anime, cartoons, drawn/illustrated)
            - 3D computer animation (CGI, Pixar-style, stylized rendering)
            - Game engine visuals (e.g., machinima, cinematic game footage, gameplay-centered videos without prominent real-world presenter)
            - Digital puppet/rig animation (e.g., VTuber models)
            - Motion graphics, stylized digital art, kinetic typography
            - Stop-motion, claymation, puppetry
            - Any mixed media where the **dominant style matches examples like Hazbin Hotel, Amazing Digital Circus, Palworld, RWBY, Meta Runner, Murder Drones**.
        - LIVE-ACTION content:
            - Content primarily consisting of **footage captured from real life**:
            - Real people, places, and environments filmed by a camera
            - Vlogs, interviews, tutorials, reviews
            - Music videos featuring live performers
            - Documentary-style footage
            - Webcam commentary videos where real people are clearly visible, even if discussing animated/gaming content
        Key principle:
        If the dominant presentation is not real-world footage of humans or environments, classify as `ANIMATED`.
        Respond with ONLY one word:
        - `ANIMATED`
        - `LIVE-ACTION`


        Your response:
        """
        
        # Ask Gemini
        response = model.generate_content(prompt)
        raw_response = response.text.strip()
        
        logger.info(f"Gemini raw response: {raw_response}")
        
        # Parse response
        response_upper = raw_response.upper()
        is_animated_video = "ANIMATED" in response_upper and "LIVE-ACTION" not in response_upper
        
        # Log result
        result_text = "Animated" if is_animated_video else "Live-action"
        logger.info(f"Classification: {raw_response} -> {result_text}")
        
        return is_animated_video
        
    except Exception as e:
        logger.error(f"Error processing video {video_url}: {str(e)}")
        return False