#!/usr/bin/env python3
"""
Quick script to check how many videos are marked as animated
"""

from cloud_database import CloudDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        db = CloudDatabase()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total videos
            cursor.execute("SELECT COUNT(*) FROM videos_full")
            total_videos = cursor.fetchone()[0]
            
            # Animated videos
            cursor.execute("SELECT COUNT(*) FROM videos_full WHERE is_animated = true")
            animated_videos = cursor.fetchone()[0]
            
            # Non-animated videos
            cursor.execute("SELECT COUNT(*) FROM videos_full WHERE is_animated = false")
            non_animated_videos = cursor.fetchone()[0]
            
            print("="*50)
            print("📊 DATABASE VIDEO COUNTS")
            print("="*50)
            print(f"Total videos: {total_videos:,}")
            print(f"Marked as ANIMATED: {animated_videos:,}")
            print(f"Marked as NOT animated: {non_animated_videos:,}")
            print(f"Percentage animated: {(animated_videos/total_videos*100):.1f}%")
            print("="*50)
            
            # Time estimate
            print("⏰ RECLASSIFICATION TIME ESTIMATES:")
            print(f"At 1 video/second: {animated_videos/60:.0f} minutes ({animated_videos/3600:.1f} hours)")
            print(f"At 2 videos/second: {animated_videos/120:.0f} minutes ({animated_videos/7200:.1f} hours)")
            print("="*50)
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main() 