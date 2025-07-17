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
        Please analyze this YouTube video and determine if it's ANIMATED or LIVE-ACTION content.

        YouTube URL: {video_url}

        ANIMATED content includes:
        - Traditional 2D animation (cartoons, anime)
        - 3D computer animation (Pixar-style, CGI movies/shows)
        - Motion graphics and digital animations
        - Game footage with animated characters
        - Drawn/illustrated content and characters
        - Stop-motion animation
        - Mixed media with predominantly animated elements

        LIVE-ACTION content includes:
        - Real people (vlogs, tutorials, interviews, reviews)
        - Documentary footage with real people/places
        - Live-recorded content with real actors
        - Real-world photography and videography
        - Gaming videos with real people (even if game is animated)
        - Music videos with real performers

        Please respond with ONLY one word:
        - "ANIMATED" if the video is primarily animated content
        - "LIVE-ACTION" if the video is primarily live-action content

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