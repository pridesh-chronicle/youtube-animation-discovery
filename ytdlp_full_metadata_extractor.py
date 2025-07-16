#!/usr/bin/env python3
"""
Full yt-dlp metadata extractor - extracts ALL available metadata from YouTube videos
including recommendations, related videos, and every possible field.

Run independently: python ytdlp_full_metadata_extractor.py
"""

import yt_dlp
import json
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime

def extract_full_metadata(url: str, output_dir: str = "full_metadata") -> Optional[str]:
    """
    Extract ALL possible metadata from a YouTube video using yt-dlp.
    
    Args:
        url: YouTube video URL
        output_dir: Directory to save metadata JSON file
        
    Returns:
        Path to saved JSON file or None if extraction failed
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract video ID from URL
        video_id = url.split('v=')[-1].split('&')[0] if 'v=' in url else url.split('/')[-1]
        
        print(f"🔍 Extracting full metadata for video: {video_id}")
        print(f"📺 URL: {url}")
        
        # Configure yt-dlp for maximum metadata extraction
        ydl_opts = {
            'quiet': False,  # Show verbose output to see what's being extracted
            'no_warnings': False,
            'extract_flat': False,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'writethumbnail': False,  # Don't download thumbnails
            'writedescription': False,  # Don't write separate description file
            'writeinfojson': False,  # We'll handle JSON ourselves
            'ignoreerrors': True,
            'no_check_certificate': True,
            # Extract playlist info if video is in playlist
            'extractaudio': False,
            'extractvideo': False,
            # Get maximum format information
            'listformats': False,
            'listsubtitles': False,
            # Additional options for comprehensive extraction
            'geo_bypass': True,
            'geo_bypass_country': 'US',
        }
        
        print("🚀 Starting extraction...")
        
        # Extract metadata
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            
            if not info_dict:
                print(f"❌ Failed to extract metadata for {video_id}")
                return None
            
            print(f"✅ Successfully extracted metadata!")
            print(f"📊 Total fields extracted: {len(info_dict.keys())}")
            
            # Convert all data to JSON-serializable format
            serializable_data = convert_to_serializable(info_dict)
            
            # Add extraction metadata
            serializable_data['_extraction_metadata'] = {
                'extraction_timestamp': datetime.now().isoformat(),
                'extraction_tool': 'yt-dlp',
                'extraction_url': url,
                'extraction_video_id': video_id,
                'total_fields_extracted': len(info_dict.keys()),
                'yt_dlp_version': yt_dlp.__version__ if hasattr(yt_dlp, '__version__') else 'unknown'
            }
            
            # Save to JSON file
            output_file = os.path.join(output_dir, f"{video_id}_full_metadata.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Full metadata saved to: {output_file}")
            
            # Print summary of key fields
            print_metadata_summary(serializable_data)
            
            return output_file
            
    except Exception as e:
        print(f"❌ Error extracting full metadata: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def convert_to_serializable(obj):
    """Recursively convert objects to JSON-serializable format."""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            try:
                # Try to serialize the value
                json.dumps(value)
                result[key] = convert_to_serializable(value)
            except (TypeError, ValueError):
                # If not serializable, convert to string representation
                if hasattr(value, '__dict__'):
                    result[key] = f"<object: {type(value).__name__}>"
                elif callable(value):
                    result[key] = f"<function: {value.__name__ if hasattr(value, '__name__') else 'anonymous'}>"
                else:
                    result[key] = str(value)
        return result
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # For other types, convert to string
        return str(obj)

def print_metadata_summary(metadata: Dict[str, Any]):
    """Print a summary of the extracted metadata."""
    print("\n📋 METADATA SUMMARY")
    print("=" * 50)
    
    # Basic video info
    basic_fields = [
        'title', 'uploader', 'upload_date', 'duration', 'view_count',
        'like_count', 'comment_count', 'channel', 'channel_id'
    ]
    
    print("🎬 Basic Info:")
    for field in basic_fields:
        if field in metadata:
            print(f"  {field}: {metadata[field]}")
    
    # Technical info
    technical_fields = [
        'format_id', 'ext', 'resolution', 'fps', 'vbr', 'abr',
        'filesize', 'protocol', 'format_note'
    ]
    
    print("\n🔧 Technical Info:")
    for field in technical_fields:
        if field in metadata:
            print(f"  {field}: {metadata[field]}")
    
    # Special fields of interest
    special_fields = [
        'categories', 'tags', 'automatic_captions', 'subtitles',
        'thumbnails', 'formats', 'age_limit', 'availability'
    ]
    
    print("\n🎯 Special Fields:")
    for field in special_fields:
        if field in metadata:
            if isinstance(metadata[field], list):
                print(f"  {field}: {len(metadata[field])} items")
            elif isinstance(metadata[field], dict):
                print(f"  {field}: {len(metadata[field])} keys")
            else:
                print(f"  {field}: {metadata[field]}")
    
    # Look for recommendation-related fields
    recommendation_fields = []
    for key in metadata.keys():
        if any(term in key.lower() for term in ['recommend', 'related', 'suggest', 'next', 'playlist']):
            recommendation_fields.append(key)
    
    if recommendation_fields:
        print("\n🔗 Recommendation Fields Found:")
        for field in recommendation_fields:
            if isinstance(metadata[field], list):
                print(f"  {field}: {len(metadata[field])} items")
            elif isinstance(metadata[field], dict):
                print(f"  {field}: {len(metadata[field])} keys")
            else:
                print(f"  {field}: {metadata[field]}")
    else:
        print("\n🔗 No explicit recommendation fields found")
    
    # Count all fields
    print(f"\n📊 Total Fields Extracted: {len(metadata.keys())}")
    
    # Show all field names for reference
    print("\n📝 All Available Fields:")
    field_names = sorted(metadata.keys())
    for i, field in enumerate(field_names):
        if i % 5 == 0:
            print()
        print(f"{field:<25}", end="")
    print("\n")

def extract_recommendations_specifically(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Look for any recommendation-related data in the metadata.
    """
    recommendations = {}
    
    # Search for recommendation-related fields
    recommendation_keywords = [
        'recommend', 'related', 'suggest', 'next', 'playlist',
        'continuation', 'endscreen', 'cards', 'annotations'
    ]
    
    for key, value in metadata.items():
        key_lower = key.lower()
        if any(keyword in key_lower for keyword in recommendation_keywords):
            recommendations[key] = value
    
    # Also check for nested recommendation data
    if 'webpage_json' in metadata:
        try:
            webpage_data = json.loads(metadata['webpage_json']) if isinstance(metadata['webpage_json'], str) else metadata['webpage_json']
            # Look for recommendation data in webpage JSON
            for key, value in webpage_data.items():
                key_lower = key.lower()
                if any(keyword in key_lower for keyword in recommendation_keywords):
                    recommendations[f"webpage_{key}"] = value
        except:
            pass
    
    return recommendations

def main():
    """Main function for standalone execution."""
    if len(sys.argv) < 2:
        print("Usage: python ytdlp_full_metadata_extractor.py <youtube_url>")
        print("\nExample:")
        print("python ytdlp_full_metadata_extractor.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        return
    
    url = sys.argv[1]
    
    print("🎬 yt-dlp Full Metadata Extractor")
    print("=" * 40)
    
    # Extract full metadata
    output_file = extract_full_metadata(url)
    
    if output_file:
        print(f"\n✅ SUCCESS!")
        print(f"📁 Metadata saved to: {output_file}")
        
        # Load and analyze for recommendations
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            recommendations = extract_recommendations_specifically(metadata)
            if recommendations:
                print(f"\n🔗 Found {len(recommendations)} recommendation-related fields:")
                for key in recommendations.keys():
                    print(f"  - {key}")
            else:
                print("\n🔗 No recommendation fields detected")
                print("💡 Note: YouTube may not provide direct recommendation data via yt-dlp")
                print("💡 Recommendations are typically generated dynamically on the frontend")
        
        except Exception as e:
            print(f"❌ Error analyzing recommendations: {e}")
    else:
        print(f"\n❌ FAILED to extract metadata")

if __name__ == "__main__":
    main()