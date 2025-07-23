#!/usr/bin/env python3
"""
Database Enhancement Script for BrightData Fields - FIXED VERSION

This script enhances the existing videos_full table with additional BrightData API fields
that weren't collected initially. It adds new columns to the schema and populates them
by making fresh API calls to BrightData.

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'database_enhancement_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseEnhancer:
    """Enhances database with additional BrightData fields"""
    
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
        """Get videos that need enhancement (missing new fields)"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for videos that haven't been enhanced yet (missing music field as indicator)
                query = """
                    SELECT video_id, title, url, youtuber, views, discovered_at
                    FROM videos_full 
                    WHERE music IS NULL
                    AND url IS NOT NULL
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
                
                logger.info(f"Found {len(videos)} videos needing enhancement")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching videos for enhancement: {str(e)}")
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
            
            # Process each result
            for i, video_data in enumerate(brightdata_results):
                try:
                    if i >= len(videos):
                        logger.warning(f"More results than expected from API: {len(brightdata_results)} vs {len(videos)}")
                        break
                    
                    original_video = videos[i]
                    video_id = original_video['video_id']
                    
                    # Extract new fields from BrightData response
                    enhancement_data = self.extract_enhancement_fields(video_data)
                    
                    # Update database with new fields
                    if self.update_video_enhancement(video_id, enhancement_data):
                        results["success"] += 1
                        logger.info(f"Enhanced video {video_id}", extra={
                            "title": original_video.get('title', ''),
                            "new_fields": len([k for k, v in enhancement_data.items() if v is not None])
                        })
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Failed to update {video_id}")
                        
                except Exception as e:
                    results["failed"] += 1
                    error_msg = f"Error processing video {i}: {str(e)}"
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
        
        # If it's already a string, check if it's valid JSON
        if isinstance(data, str):
            try:
                json.loads(data)  # Validate it's valid JSON
                return data
            except (json.JSONDecodeError, ValueError):
                # If it's not valid JSON, wrap it in quotes
                return json.dumps(data)
        
        # For all other types (dict, list, etc.), convert to JSON
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to convert data to JSON: {data}, error: {e}")
            # Fallback: convert to string and then to JSON
            return json.dumps(str(data))
    
    def extract_enhancement_fields(self, video_data: Dict) -> Dict:
        """Extract the new enhancement fields from BrightData response"""
        
        enhancement_fields = {
            # Music and Media - simple text fields
            'music': video_data.get('music'),
            'preview_image': video_data.get('preview_image'),
            'shortcode': video_data.get('shortcode'),
            'avatar_img_channel': video_data.get('avatar_img_channel'),
            
            # Monetization and Sponsorship - simple fields
            'is_sponsored': video_data.get('is_sponsored'),
            'license': video_data.get('license'),
            
            # Technical Video Details - JSONB fields need special handling
            'viewport_frames': self.safe_json_convert(video_data.get('viewport_frames')),
            'current_optimal_res': video_data.get('current_optimal_res'),
            'color': video_data.get('color'),
            'quality': video_data.get('quality'),
            'post_type': video_data.get('post_type'),
            
            # Enhanced Channel Info
            'youtuber_id': video_data.get('youtuber_id'),
            
            # Enhanced Transcript Data - JSONB fields need special handling
            'transcript': self.safe_json_convert(video_data.get('transcript')),
            'transcript_language': video_data.get('transcript_language'),
            'chapters': self.safe_json_convert(video_data.get('chapters'))
        }
        
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
                    if field_value is not None:
                        set_clauses.append(f"{field_name} = %s")
                        values.append(field_value)
                
                if not set_clauses:
                    logger.warning(f"No enhancement data to update for {video_id}")
                    return True
                
                query = f"""
                    UPDATE videos_full 
                    SET {', '.join(set_clauses)}
                    WHERE video_id = %s
                """
                
                values.append(video_id)
                
                # Debug log the query and values
                logger.debug(f"Executing query for {video_id}: {query}")
                logger.debug(f"Values: {[type(v).__name__ for v in values]}")
                
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
            return False
    
    def enhance_database(self, limit: Optional[int] = None, dry_run: bool = False) -> Dict:
        """Main method to enhance the entire database"""
        
        logger.info("🚀 Starting database enhancement process", extra={
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
                
                # Rate limiting: wait between batches
                if i + self.batch_size < len(videos_to_enhance):
                    wait_time = 2  # seconds
                    logger.info(f"Waiting {wait_time}s before next batch...")
                    time.sleep(wait_time)
                
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