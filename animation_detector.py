import os
import tempfile
import shutil
import logging
from downloader import download_video
from frame_extractor import extract_frames
from animation_checker import analyze_video_frames

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_animated(video_url, save_videos=False, save_frames=False):
    """
    Determine if a YouTube video is animated or live-action.
    
    Args:
        video_url (str): YouTube video URL
        save_videos (bool): Whether to save videos to persistent storage
        save_frames (bool): Whether to save frames to persistent storage
        
    Returns:
        bool: True if animated, False if live-action
    """
    temp_dir = None
    video_path = None
    
    try:
        # Create temporary directory for this video
        temp_dir = tempfile.mkdtemp(prefix="ytdl_")
        video_path = os.path.join(temp_dir, "video.mp4")
        
        logger.info(f"Processing video: {video_url}")
        
        # Download video
        download_video(video_url, video_path, save_to_persistent=save_videos)
        
        # Extract frames
        frames_dir = os.path.join(temp_dir, "frames")
        frame_paths = extract_frames(video_path, video_url, frames_dir, save_to_persistent=save_frames)
        
        # Analyze frames with Gemini
        classification = analyze_video_frames(frame_paths)
        
        # Parse classification result
        classification_clean = classification.lower().strip()
        is_animated_video = classification_clean == "true"
        
        logger.info(f"Classification: {classification} -> {'Animated' if is_animated_video else 'Live-action'}")
        
        return is_animated_video
        
    except Exception as e:
        logger.error(f"Error processing video {video_url}: {str(e)}")
        return False
        
    finally:
        # Clean up temporary files (always clean temp dir, persistent files are saved separately)
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory {temp_dir}: {str(e)}")