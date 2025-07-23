#!/usr/bin/env python3
"""
Database Enhancement Script for BrightData Fields - ANIMATED VIDEOS ONLY

This script enhances ANIMATED videos in the videos_full table with additional BrightData API 
fields that weren't collected initially. It adds new columns to the schema and populates them
by making fresh API calls to BrightData for videos marked as is_animated = true.

New fields added:
- music, preview_image, shortcode, avatar_img_channel, is_sponsored
- license, viewport_frames, current_optimal_res, color, quality  
- post_type, youtuber_id, transcript, transcript_language, chapters

Usage:
    python enhance_database.py [--batch-size N] [--limit N] [--dry-run]
"""

import os
import sys
import logging
import argparse
import time
import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv

# Import existing modules
from cloud_database import CloudDatabase
from api_client import BrightDataClient, BrightDataTimeoutError, BrightDataAPIError

# Load environment variables
load_dotenv()

# Configure logging with different levels for file and console
log_filename = f'database_enhancement_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create file handler with DEBUG level
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

# Create console handler with INFO level
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class DatabaseEnhancer:
    """Enhances animated videos in database with additional BrightData fields"""
    
    def __init__(self, batch_size: int = 10):
        """Initialize the database enhancer"""
        self.cloud_db = CloudDatabase()
        self.brightdata_client = BrightDataClient()
        self.batch_size = batch_size
        
        logger.info("Database Enhancer initialized", extra={
            "batch_size": batch_size
        })
    
    def add_new_columns(self, dry_run: bool = False) -> bool:
        """Add new columns to the database schema"""
        
        new_columns = {
            # Music and Media
            'music': 'TEXT',
            'preview_image': 'TEXT',
            'shortcode': 'TEXT',
            'avatar_img_channel': 'TEXT',
            
            # Monetization and Sponsorship
            'is_sponsored': 'BOOLEAN',
            'license': 'TEXT',
            
            # Technical Video Details
            'viewport_frames': 'JSONB',
            'current_optimal_res': 'TEXT',
            'color': 'TEXT',
            'quality': 'TEXT',
            'post_type': 'TEXT',
            
            # Enhanced Channel Info
            'youtuber_id': 'TEXT',
            
            # Enhanced Transcript Data  
            'transcript': 'JSONB',
            'transcript_language': 'TEXT',
            'chapters': 'JSONB'
        }
        
        logger.info(f"Adding {len(new_columns)} new columns to videos_full table")
        
        if dry_run:
            logger.info("DRY RUN: Would add the following columns:")
            for column, datatype in new_columns.items():
                logger.info(f"  - {column}: {datatype}")
            return True
        
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                added_columns = []
                for column_name, datatype in new_columns.items():
                    try:
                        # Check if column already exists
                        cursor.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'videos_full' 
                            AND column_name = %s
                        """, (column_name,))
                        
                        if cursor.fetchone():
                            logger.info(f"Column {column_name} already exists, skipping")
                            continue
                        
                        # Add the column
                        alter_sql = f"ALTER TABLE videos_full ADD COLUMN {column_name} {datatype}"
                        cursor.execute(alter_sql)
                        added_columns.append(column_name)
                        
                        logger.info(f"Added column: {column_name} ({datatype})")
                        
                    except Exception as e:
                        logger.error(f"Failed to add column {column_name}: {str(e)}")
                        continue
                
                conn.commit()
                
                logger.info(f"Successfully added {len(added_columns)} new columns", extra={
                    "added_columns": added_columns
                })
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to add new columns: {str(e)}")
            return False
    
    def get_videos_to_enhance(self, limit: Optional[int] = None) -> List[Dict]:
        """Get animated videos that need enhancement (missing new fields)"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for ANIMATED videos that haven't been enhanced yet (missing music field as indicator)
                query = """
                    SELECT video_id, title, url, youtuber, views, discovered_at
                    FROM videos_full 
                    WHERE TRUE  -- Process ALL videos to fix corruption
                    AND url IS NOT NULL
                    AND is_animated = true
                    ORDER BY views DESC NULLS LAST, discovered_at DESC
                """
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries
                columns = [desc[0] for desc in cursor.description]
                videos = []
                
                for row in rows:
                    video_dict = dict(zip(columns, row))
                    videos.append(video_dict)
                
                logger.info(f"Found {len(videos)} animated videos needing enhancement")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching animated videos for enhancement: {str(e)}")
            return []
    
    def enhance_video_batch(self, videos: List[Dict], dry_run: bool = False) -> Dict:
        """Enhance a batch of videos with BrightData API"""
        
        if not videos:
            return {"success": 0, "failed": 0, "errors": []}
        
        video_urls = [video['url'] for video in videos]
        video_ids = [video['video_id'] for video in videos]
        
        logger.info(f"Enhancing batch of {len(videos)} videos", extra={
            "video_ids": video_ids[:5] + ["..."] if len(video_ids) > 5 else video_ids
        })
        
        if dry_run:
            logger.info("DRY RUN: Would enhance videos:", extra={"urls": video_urls})
            return {"success": len(videos), "failed": 0, "errors": []}
        
        results = {"success": 0, "failed": 0, "errors": []}
        
        try:
            # Make BrightData API call
            brightdata_results = self.brightdata_client.fetch_videos(video_urls)
            
            if not brightdata_results:
                logger.warning("No results returned from BrightData API")
                results["failed"] = len(videos)
                results["errors"].append("No results from BrightData API")
                return results
            
            # Create mapping from URL to original video data for proper matching
            url_to_video = {video['url']: video for video in videos}
            
            # Process each result - match by URL, not by array index!
            for video_data in brightdata_results:
                try:
                    # Get the original URL from the BrightData response
                    response_url = video_data.get('url')
                    if not response_url:
                        logger.warning("No URL in BrightData response, skipping")
                        results["failed"] += 1
                        results["errors"].append("No URL in BrightData response")
                        continue
                    
                    # Find the matching original video data
                    original_video = url_to_video.get(response_url)
                    if not original_video:
                        logger.warning(f"No matching original video found for URL: {response_url}")
                        results["failed"] += 1
                        results["errors"].append(f"No matching original video for URL: {response_url}")
                        continue
                    
                    video_id = original_video['video_id']
                    
                    # Verify the video_id matches (additional safety check)
                    response_video_id = video_data.get('video_id')
                    if response_video_id and response_video_id != video_id:
                        logger.warning(f"Video ID mismatch: DB={video_id}, API={response_video_id}, URL={response_url}")
                        # Use the video_id from our database (the source of truth)
                    
                    # Extract new fields from BrightData response
                    enhancement_data = self.extract_enhancement_fields(video_data)
                    
                    # Update database with new fields
                    if self.update_video_enhancement(video_id, enhancement_data):
                        results["success"] += 1
                        logger.info(f"Enhanced video {video_id}", extra={
                            "title": original_video.get('title', ''),
                            "response_url": response_url,
                            "new_fields": len([k for k, v in enhancement_data.items() if v is not None])
                        })
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Failed to update {video_id}")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Error processing video response: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(error_msg)
                    continue
            
        except (BrightDataTimeoutError, BrightDataAPIError) as e:
            logger.error(f"BrightData API error: {str(e)}")
            results["failed"] = len(videos)
            results["errors"].append(f"BrightData API error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error in batch enhancement: {str(e)}")
            results["failed"] = len(videos)
            results["errors"].append(f"Unexpected error: {str(e)}")
        
        return results
    
    def safe_json_convert(self, data: Any) -> Optional[str]:
        """Safely convert data to JSON string for PostgreSQL JSONB fields"""
        if data is None:
            return None
        
        logger.debug(f"Converting to JSON: {type(data).__name__} = {data}")
        
        # If it's already a string, check if it's valid JSON
        if isinstance(data, str):
            try:
                json.loads(data)  # Validate it's valid JSON
                logger.debug(f"Already valid JSON string: {data}")
                return data
            except (json.JSONDecodeError, ValueError):
                # If it's not valid JSON, wrap it in quotes
                result = json.dumps(data)
                logger.debug(f"Converted string to JSON: {result}")
                return result
        
        # For all other types (dict, list, etc.), convert to JSON
        try:
            result = json.dumps(data, ensure_ascii=False, default=str)
            logger.debug(f"Converted {type(data).__name__} to JSON: {result}")
            return result
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to convert data to JSON: {data}, error: {e}")
            # Fallback: convert to string and then to JSON
            result = json.dumps(str(data))
            logger.debug(f"Fallback conversion: {result}")
            return result
    
    def safe_extract_field(self, video_data: Dict, field_name: str, force_json: bool = False) -> Any:
        """Safely extract a field, converting to JSON if needed"""
        value = video_data.get(field_name)
        if value is None:
            return None
        
        # If it's a dict or list, or force_json is True, convert to JSON
        if force_json or isinstance(value, (dict, list)):
            return self.safe_json_convert(value)
        
        # For simple types, return as-is
        return value
    
    def extract_enhancement_fields(self, video_data: Dict) -> Dict:
        """Extract the new enhancement fields from BrightData response"""
        
        logger.debug(f"Raw video data keys: {list(video_data.keys())}")
        
        enhancement_fields = {
            # Music and Media - defensive extraction
            'music': self.safe_extract_field(video_data, 'music'),
            'preview_image': self.safe_extract_field(video_data, 'preview_image'),
            'shortcode': self.safe_extract_field(video_data, 'shortcode'),
            'avatar_img_channel': self.safe_extract_field(video_data, 'avatar_img_channel'),
            
            # Monetization and Sponsorship
            'is_sponsored': self.safe_extract_field(video_data, 'is_sponsored'),
            'license': self.safe_extract_field(video_data, 'license'),
            
            # Technical Video Details - force JSON for potentially complex fields
            'viewport_frames': self.safe_extract_field(video_data, 'viewport_frames', force_json=True),
            'current_optimal_res': self.safe_extract_field(video_data, 'current_optimal_res'),
            'color': self.safe_extract_field(video_data, 'color'),
            'quality': self.safe_extract_field(video_data, 'quality'),
            'post_type': self.safe_extract_field(video_data, 'post_type'),
            
            # Enhanced Channel Info
            'youtuber_id': self.safe_extract_field(video_data, 'youtuber_id'),
            
            # Enhanced Transcript Data - force JSON for complex fields
            'transcript': self.safe_extract_field(video_data, 'transcript', force_json=True),
            'transcript_language': self.safe_extract_field(video_data, 'transcript_language'),
            'chapters': self.safe_extract_field(video_data, 'chapters', force_json=True)
        }
        
        # Debug: Log all field types
        for field_name, field_value in enhancement_fields.items():
            if field_value is not None:
                logger.debug(f"Field {field_name}: {type(field_value).__name__} = {field_value}")
        
        # Count non-null fields
        non_null_count = len([k for k, v in enhancement_fields.items() if v is not None])
        logger.debug(f"Extracted {non_null_count} non-null enhancement fields")
        
        return enhancement_fields
    
    def update_video_enhancement(self, video_id: str, enhancement_data: Dict) -> bool:
        """Update a video record with enhancement data"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic UPDATE query
                set_clauses = []
                values = []
                
                for field_name, field_value in enhancement_data.items():
                    # Process ALL fields including None values to fix corruption
                    # Debug: Check data type before adding to query
                    if isinstance(field_value, (dict, list)):
                        logger.error(f"FOUND DICT/LIST in {field_name}: {type(field_value)} - {field_value}")
                        return False
                    
                    set_clauses.append(f"{field_name} = %s")
                    values.append(field_value)
                    
                    # Debug logging
                    logger.debug(f"Adding field {field_name}: {type(field_value).__name__} = {field_value}")
                
                if not set_clauses:
                    logger.warning(f"No enhancement data to update for {video_id}")
                    return True
                
                query = f"""
                    UPDATE videos_full 
                    SET {', '.join(set_clauses)}
                    WHERE video_id = %s
                """
                
                values.append(video_id)
                
                # Debug: Log all value types
                logger.debug(f"Final values for {video_id}: {[type(v).__name__ for v in values]}")
                
                cursor.execute(query, values)
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"Updated {cursor.rowcount} row(s) for video {video_id}")
                    return True
                else:
                    logger.warning(f"No rows updated for video_id: {video_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating video {video_id}: {str(e)}")
            logger.error(f"Enhancement data types: {[(k, type(v).__name__) for k, v in enhancement_data.items()]}")
            return False
    
    def enhance_database(self, limit: Optional[int] = None, dry_run: bool = False) -> Dict:
        """Main method to enhance the entire database"""
        
        logger.info("🚀 Starting animated video enhancement process", extra={
            "limit": limit,
            "batch_size": self.batch_size,
            "dry_run": dry_run
        })
        
        # Step 1: Add new columns
        logger.info("Step 1: Adding new columns to schema...")
        if not self.add_new_columns(dry_run):
            logger.error("Failed to add new columns, aborting")
            return {"error": "Failed to add new columns"}
        
        # Step 2: Get videos to enhance
        logger.info("Step 2: Fetching videos to enhance...")
        videos_to_enhance = self.get_videos_to_enhance(limit)
        
        if not videos_to_enhance:
            logger.info("No videos found that need enhancement")
            return {"message": "No videos to enhance", "total_videos": 0}
        
        # Step 3: Process in batches
        logger.info(f"Step 3: Processing {len(videos_to_enhance)} videos in batches of {self.batch_size}...")
        
        total_results = {"success": 0, "failed": 0, "errors": []}
        
        for i in range(0, len(videos_to_enhance), self.batch_size):
            batch = videos_to_enhance[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(videos_to_enhance) + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} videos)")
            
            try:
                batch_results = self.enhance_video_batch(batch, dry_run)
                
                # Accumulate results
                total_results["success"] += batch_results["success"]
                total_results["failed"] += batch_results["failed"]
                total_results["errors"].extend(batch_results["errors"])
                
                logger.info(f"Batch {batch_num} completed", extra={
                    "batch_success": batch_results["success"],
                    "batch_failed": batch_results["failed"],
                    "total_success": total_results["success"],
                    "total_failed": total_results["failed"]
                })
                
                # Process immediately for maximum speed
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {str(e)}")
                total_results["failed"] += len(batch)
                total_results["errors"].append(f"Batch {batch_num} failed: {str(e)}")
                continue
        
        # Final results
        total_processed = total_results["success"] + total_results["failed"]
        success_rate = (total_results["success"] / total_processed * 100) if total_processed > 0 else 0
        
        logger.info("🎉 Database enhancement completed!", extra={
            "total_videos": len(videos_to_enhance),
            "total_processed": total_processed,
            "successful": total_results["success"],
            "failed": total_results["failed"], 
            "success_rate_percent": round(success_rate, 1),
            "dry_run": dry_run
        })
        
        return {
            "total_videos": len(videos_to_enhance),
            "processed": total_processed,
            "successful": total_results["success"],
            "failed": total_results["failed"],
            "success_rate": success_rate,
            "errors": total_results["errors"][:10],  # First 10 errors
            "dry_run": dry_run
        }

def main():
    """Main function with CLI argument parsing"""
    parser = argparse.ArgumentParser(description="Enhance database with additional BrightData fields")
    parser.add_argument('--batch-size', type=int, default=5,
                      help='Number of videos to process in each batch (default: 5)')
    parser.add_argument('--limit', type=int, default=None,
                      help='Maximum number of videos to enhance (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                      help='Perform a dry run without making actual changes')
    
    args = parser.parse_args()
    
    try:
        enhancer = DatabaseEnhancer(batch_size=args.batch_size)
        results = enhancer.enhance_database(limit=args.limit, dry_run=args.dry_run)
        
        logger.info("Enhancement process completed", extra=results)
        
        if results.get("errors"):
            logger.warning(f"Process completed with {len(results['errors'])} errors")
            sys.exit(1)
        else:
            logger.info("Process completed successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 