import subprocess
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs

def extract_video_id(url: str) -> str:
    """
    Extract the YouTube video ID from a URL.
    Supports standard watch URLs and short links.
    """
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        return parse_qs(parsed.query).get("v", [None])[0]
    elif "youtu.be" in parsed.netloc:
        return parsed.path.lstrip("/")
    else:
        raise ValueError("Unsupported YouTube URL format")

def get_video_duration(video_path):
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])

def extract_frames(video_path, video_url, base_output_dir="frames", frame_count=10):
    video_id = extract_video_id(video_url)
    output_dir = Path(base_output_dir) / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    duration = get_video_duration(video_path)
    interval = duration / frame_count

    extracted_frames = []
    for i in range(frame_count):
        timestamp = i * interval
        out_file = output_dir / f"frame_{i:03d}.png"
        command = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            str(out_file)
        ]
        subprocess.run(command, check=True)
        extracted_frames.append(out_file)

    return extracted_frames
