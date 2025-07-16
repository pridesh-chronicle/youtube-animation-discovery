import yt_dlp
import json
import os
from typing import Dict, Any, Optional

def extract_ytdlp_metadata(url: str, video_id: str, output_dir: str = "metadata", save_json: bool = True) -> Optional[Dict[str, Any]]:
    """
    Extract comprehensive metadata from a YouTube video using yt-dlp.
    
    Args:
        url: YouTube video URL
        video_id: YouTube video ID
        output_dir: Directory to save metadata JSON file
        save_json: Whether to save separate JSON file (default: True)
        
    Returns:
        Dictionary with ytdlp_ prefixed keys or None if extraction failed
    """
    try:
        # Ensure output directory exists only if saving JSON
        if save_json:
            os.makedirs(output_dir, exist_ok=True)
        
        # Configure yt-dlp for metadata extraction only
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'writedescription': False,
            'writeinfojson': False,
        }
        
        # Extract metadata
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            if not info_dict:
                print(f"❌ Failed to extract metadata for {video_id}")
                return None
                
            # Clean up the metadata by removing non-serializable objects
            clean_metadata = {}
            
            # Copy all serializable fields with ytdlp_ prefix
            prefixed_metadata = {}
            for key, value in info_dict.items():
                try:
                    # Test if the value is JSON serializable
                    json.dumps(value)
                    prefixed_metadata[f"ytdlp_{key}"] = value
                except (TypeError, ValueError):
                    # Skip non-serializable values but keep the key with a note
                    prefixed_metadata[f"ytdlp_{key}"] = f"<non-serializable: {type(value).__name__}>"
            
            # Add extraction metadata with prefix
            prefixed_metadata['ytdlp_extraction_info'] = {
                'extractor': 'yt-dlp',
                'extraction_timestamp': info_dict.get('timestamp'),
                'video_id_extracted': video_id,
                'original_url': url
            }
            
            # Store clean_metadata for file saving (original format)
            clean_metadata = prefixed_metadata.copy()
            # Remove prefix for file saving to maintain compatibility
            for key, value in prefixed_metadata.items():
                if key.startswith('ytdlp_'):
                    clean_metadata[key[6:]] = value  # Remove 'ytdlp_' prefix for file
            
            # Save to JSON file only if save_json is True
            if save_json:
                output_file = os.path.join(output_dir, f"{video_id}_ytdlp.json")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(clean_metadata, f, indent=2, ensure_ascii=False)
                
                print(f"✅ yt-dlp metadata saved: {output_file}")
            else:
                print(f"✅ yt-dlp metadata extracted (no JSON file saved)")
            
            return prefixed_metadata
            
    except Exception as e:
        print(f"❌ Error extracting yt-dlp metadata for {video_id}: {str(e)}")
        return None

def get_additional_fields_summary(metadata_file: str) -> Dict[str, Any]:
    """
    Load and summarize additional fields from yt-dlp metadata that aren't in BrightData.
    
    Args:
        metadata_file: Path to the JSON metadata file
        
    Returns:
        Dictionary with key additional fields
    """
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Key additional fields that yt-dlp provides
        additional_fields = {
            'technical': {
                'fps': metadata.get('fps'),
                'vbr': metadata.get('vbr'),
                'abr': metadata.get('abr'),
                'asr': metadata.get('asr'),
                'filesize': metadata.get('filesize'),
                'format_id': metadata.get('format_id'),
                'protocol': metadata.get('protocol'),
                'ext': metadata.get('ext'),
                'format_note': metadata.get('format_note'),
            },
            'content': {
                'categories': metadata.get('categories'),
                'uploader_url': metadata.get('uploader_url'),
                'upload_date': metadata.get('upload_date'),
                'original_url': metadata.get('original_url'),
                'webpage_url': metadata.get('webpage_url'),
                'fulltitle': metadata.get('fulltitle'),
            },
            'availability': {
                'age_limit': metadata.get('age_limit'),
                'availability': metadata.get('availability'),
                'is_live': metadata.get('is_live'),
                'was_live': metadata.get('was_live'),
                'live_status': metadata.get('live_status'),
            },
            'media': {
                'thumbnails_count': len(metadata.get('thumbnails', [])),
                'automatic_captions_langs': list(metadata.get('automatic_captions', {}).keys()),
                'subtitles_langs': list(metadata.get('subtitles', {}).keys()),
                'duration_string': metadata.get('duration_string'),
                'start_time': metadata.get('start_time'),
                'end_time': metadata.get('end_time'),
            }
        }
        
        return additional_fields
        
    except Exception as e:
        print(f"❌ Error reading metadata summary: {str(e)}")
        return {}

if __name__ == "__main__":
    # Test the extractor
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    test_video_id = "dQw4w9WgXcQ"
    
    metadata_file = extract_ytdlp_metadata(test_url, test_video_id)
    if metadata_file:
        summary = get_additional_fields_summary(metadata_file)
        print("\n📊 Additional fields summary:")
        print(json.dumps(summary, indent=2))