import yt_dlp
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs

def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from a URL."""
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [None])[0]
    elif "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/")
    else:
        raise ValueError("Unsupported YouTube URL format")

def download_video(url, output_path="video.mp4", save_to_persistent=False):
    """
    Download a YouTube video.
    
    Args:
        url (str): YouTube video URL
        output_path (str): Path where video should be saved temporarily
        save_to_persistent (bool): Whether to also save to persistent videos/ folder
    
    Returns:
        str: Path to the downloaded video file
    """
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
        'merge_output_format': 'mp4',
        'quiet': True,
        'overwrites': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # If save_to_persistent is True, also save to videos/{video_id}/ folder
    if save_to_persistent:
        video_id = extract_video_id(url)
        persistent_dir = Path("videos") / video_id
        persistent_dir.mkdir(parents=True, exist_ok=True)
        persistent_path = persistent_dir / "video.mp4"
        
        # Copy the file to persistent location
        shutil.copy2(output_path, persistent_path)
        print(f"📹 Saved video to: {persistent_path}")
    
    return output_path
