#!/usr/bin/env python3
"""
Type Classification Script for Animated Videos

This script reclassifies animated videos (is_animated = true) into specific types:
ANIMATED, HYBRID, LIVE_ACTION using detailed visual medium analysis.

Usage:
    python type_classifier.py [--batch-size N] [--limit N] [--dry-run]
"""

import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to the path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cloud_database import CloudDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TypeClassifier:
    """Classifies animated videos into specific type categories"""
    
    def __init__(self, batch_size: int = 5):
        self.cloud_db = CloudDatabase()
        self.batch_size = batch_size
        
        # Configure Gemini AI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
    def add_type_column(self, dry_run: bool = False) -> bool:
        """Add TYPE column to videos_full table if it doesn't exist"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if TYPE column exists
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'videos_full' AND column_name = 'type'
                """)
                
                if cursor.fetchone():
                    logger.info("TYPE column already exists in videos_full table")
                    return True
                
                if dry_run:
                    logger.info("DRY RUN: Would add TYPE column to videos_full table")
                    return True
                
                # Add TYPE column
                logger.info("Adding TYPE column to videos_full table")
                cursor.execute("""
                    ALTER TABLE videos_full 
                    ADD COLUMN IF NOT EXISTS type TEXT
                """)
                conn.commit()
                logger.info("Successfully added TYPE column")
                return True
                
        except Exception as e:
            logger.error(f"Error adding TYPE column: {str(e)}")
            return False
    
    def get_videos_to_classify(self, limit: Optional[int] = None) -> List[Dict]:
        """Get animated videos that need type classification"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for animated videos that haven't been type-classified yet
                query = """
                    SELECT video_id, title, url, youtuber, views, discovered_at, 
                           description, video_length, upload_date, preview_image, tags
                    FROM videos_full 
                    WHERE is_animated = true
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
                
                logger.info(f"Found {len(videos)} animated videos needing type classification")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching videos to classify: {str(e)}")
            return []
    
    def create_classification_prompt(self, video_data: Dict) -> str:
        """Create the type classification prompt for a video"""
        
        # Calculate duration in minutes
        duration_minutes = "Unknown"
        if video_data.get('video_length'):
            try:
                # Assuming video_length is in seconds
                duration_seconds = int(video_data['video_length'])
                duration_minutes = f"{duration_seconds // 60}"
            except (ValueError, TypeError):
                duration_minutes = "Unknown"
        
        # Truncate description to avoid token limits
        description = (video_data.get('description') or '')[:500]
        if len(video_data.get('description', '')) > 500:
            description += "..."
        # Format tags for better analysis
        tags = video_data.get('tags')
        tags_str = 'None'
        if tags:
            try:
                if isinstance(tags, str):
                    import json
                    tags_list = json.loads(tags)
                elif isinstance(tags, list):
                    tags_list = tags
                else:
                    tags_list = []
                
                if tags_list:
                    # Take first 8 tags to avoid token limits
                    tags_str = ', '.join(tags_list[:8])
                    if len(tags_list) > 8:
                        tags_str += f' (and {len(tags_list) - 8} more)'
            except:
                tags_str = str(tags)[:80] + '...' if len(str(tags)) > 80 else str(tags)
        
        # Get preview image for visual analysis
        preview_image = video_data.get('preview_image')

       
        prompt = f"""RECLASSIFICATION TASK: Analyze this YouTube video and determine its TYPE classification.

VIDEO METADATA:
- Title: {video_data.get('title', 'Unknown')}
- Creator: {video_data.get('youtuber', 'Unknown')}
- Duration: {duration_minutes} minutes
- URL: {video_data.get('url', '')}
- Description: {description}
- Tags: {tags_str}
- Preview Image: {preview_image if preview_image else 'Not available'}

Instruction:
Analyze the provided YouTube video metadata AND preview image (if available) to classify its primary format as exactly one of the following categories:
ANIMATED, HYBRID, LIVE_ACTION

If preview image is available, use it as PRIMARY evidence. Use metadata as SUPPORTING evidence.

Core Principle:
Classification is based on the dominant visual medium that defines the **viewer's primary experience**.

======================
TYPE: ANIMATED
======================
DESC:
Primary visuals consist entirely of created artistic movement (frame-by-frame), irrespective of narration or overlays.  
Also includes commentary/review content where the primary **subject matter** is animation.

INCLUDES:
• Traditional 2D animation (cartoons, anime, hand-drawn shorts)  
• 3D/CGI animation (Pixar, RWBY, Murder Drones)  
• Stop-motion (e.g., Coraline, Wallace & Gromit)  
• Motion graphics and infographic explainers (e.g., Kurzgesagt)  
• Fully animated music videos (e.g., Gorillaz)  
• Machinima (cinematic narratives shot in game engines, e.g., Red vs. Blue)  
• Video essays or commentary whose **main subject is animated works**, even if presenter-led

EXCLUDES:
• Gameplay-driven videos (→ HYBRID)  
• VTuber content unless reviewing animation (→ HYBRID if not animation review)  
• Art tutorials, drawing demonstrations, speedpaints (→ LIVE_ACTION)  
• Videos with real people as dominant visuals (→ LIVE_ACTION)  

======================
TYPE: HYBRID
======================
DESC:
Content characterized by substantial **blending of animated and live-action visuals** or **gameplay-driven experiences** where the game world is primary.

INCLUDES:
• Significant integration of animation and live-action (e.g., Space Jam, Who Framed Roger Rabbit)  
• VTuber streams **unless focused on animated reviews**  
• All gameplay-driven content: Let's Plays, walkthroughs, gameplay commentary, highlights  
• Hybrid music videos blending animated and real-world footage (e.g., Take On Me by A-ha)  
• Mixed media where animation and live-action are both present in roughly equal or blended ways

EXCLUDES:
• Fully animated videos (→ ANIMATED)  
• Real-world videos with minor animated overlays (→ LIVE_ACTION)  
• Reviews/commentary primarily about animation, even if live presenter-led (→ ANIMATED)

======================
TYPE: LIVE_ACTION
======================
DESC:
Primary visuals consist of real-world footage featuring real people and environments, without a substantial animated or gameplay component.

INCLUDES:
• All vlogs, lifestyle, travel videos  
• MrBeast-style challenge and stunt videos  
• Tutorials, interviews, real-world explainers  
• Reaction videos to real-world or non-animated content  
• Music videos with real performers and minimal/ancillary animation  
• VTuber streams where the dominant visual and subject is non-animation/non-gaming

EXCLUDES:
• All gameplay-driven content (→ HYBRID)  
• Videos with significant animation integration (→ HYBRID)  
• Content where animation is the primary subject (→ ANIMATED)

======================
Additional Clarifications:
======================
• Dominant Visual Test: If one format accounts for 80%+ of runtime, classify accordingly.  
• Subject Matter Rule: If core subject is animated work, → ANIMATED even if filmed live-action.  
• All gameplay = HYBRID regardless of art style or presenter.  
• VTuber streams = HYBRID unless explicitly reviewing animated content.

======================
Edge Case Examples:
======================
• Amazing Digital Circus pilot → ANIMATED  
• Minecraft machinima film → ANIMATED  
• Minecraft Let's Play → HYBRID  
• VTuber playing Elden Ring → HYBRID  
• VTuber discussing anime → ANIMATED  
• Space Jam trailer → HYBRID  
• Take On Me music video → HYBRID  
• MrBeast challenge video → LIVE_ACTION  
• Lifestyle vlog → LIVE_ACTION  
• Kurzgesagt explainer → ANIMATED

======================
RESPONSE FORMAT:
======================
You MUST respond with ONLY valid JSON in this exact format (no other text):
{{
  "classification": "ANIMATED",
  "confidence": "HIGH",
  "reason": "Brief explanation"
}}

Replace "ANIMATED" with: ANIMATED, HYBRID, LIVE_ACTION, or ERROR  
Replace "HIGH" with: HIGH, MEDIUM, or LOW  
Replace "Brief explanation" with your reasoning."""
        
        return prompt
    
    def parse_classification_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the Gemini AI response for type classification"""
        try:
            # Try to parse as JSON first
            response_data = json.loads(response_text.strip())
            
            classification = response_data.get('classification', 'ERROR').upper()
            confidence = response_data.get('confidence', 'LOW').upper()
            reason = response_data.get('reason', 'No reason provided')
            
            # Validate classification
            valid_classifications = ['ANIMATED', 'HYBRID', 'LIVE_ACTION']
            if classification not in valid_classifications:
                classification = 'ERROR'
            
            # Validate confidence
            valid_confidences = ['HIGH', 'MEDIUM', 'LOW']
            if confidence not in valid_confidences:
                confidence = 'LOW'
            
            return {
                'type': classification,
                'confidence': confidence,
                'reason': reason
            }
            
        except json.JSONDecodeError:
            # Fallback: try to extract from text
            logger.warning(f"Failed to parse JSON response, attempting text extraction")
            
            text = response_text.upper()
            classification = 'ERROR'
            
            if 'ANIMATED' in text and 'LIVE_ACTION' not in text and 'HYBRID' not in text:
                classification = 'ANIMATED'
            elif 'HYBRID' in text:
                classification = 'HYBRID'
            elif 'LIVE_ACTION' in text:
                classification = 'LIVE_ACTION'
            
            return {
                'type': classification,
                'confidence': 'LOW',
                'reason': 'Extracted from malformed response'
            }
    
    def classify_video_batch(self, videos: List[Dict], dry_run: bool = False) -> Dict:
        """Classify a batch of videos"""
        results = {
            'total': len(videos),
            'success': 0,
            'errors': 0,
            'classifications': {}
        }
        
        for video in videos:
            video_id = video['video_id']
            title = video.get('title', 'Unknown')
            
            try:
                logger.info(f"Classifying video: {video_id} - {title}")
                
                # Create prompt
                prompt = self.create_classification_prompt(video)
            
                if dry_run:
                    print(prompt[:1000])
                    logger.info(f"DRY RUN: Would classify video {video_id}")
                    results['success'] += 1
                    continue
                
                # Call Gemini AI
                max_retries = 2
                response = None
                
                for attempt in range(max_retries):
                    try:
                        response_obj = self.model.generate_content(prompt)
                        response = response_obj.text if response_obj else None
                        if response:
                            break
                    except Exception as e:
                        logger.warning(f"Attempt {attempt + 1} failed for video {video_id}: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)  # Exponential backoff
                
                if not response:
                    logger.error(f"Failed to get AI response for video {video_id}")
                    results['errors'] += 1
                    continue
                
                # Parse response
                classification_data = self.parse_classification_response(response)
                
                # Update database
                success = self.update_video_type(video_id, classification_data)
                
                if success:
                    results['success'] += 1
                    results['classifications'][classification_data['type']] = results['classifications'].get(classification_data['type'], 0) + 1
                    logger.info(f"Successfully classified {video_id} as {classification_data['type']}")
                else:
                    results['errors'] += 1
                    logger.error(f"Failed to update database for video {video_id}")
                
                # Process immediately for maximum speed
                
            except Exception as e:
                logger.error(f"Error processing video {video_id}: {str(e)}")
                results['errors'] += 1
        
        return results
    
    def update_video_type(self, video_id: str, classification_data: Dict) -> bool:
        """Update video type classification in database"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE videos_full 
                    SET type = %s
                    WHERE video_id = %s
                """, (classification_data['type'], video_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.debug(f"Updated video {video_id} with type {classification_data['type']}")
                    return True
                else:
                    logger.warning(f"No rows updated for video {video_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating video {video_id}: {str(e)}")
            return False
    
    def classify_videos(self, limit: Optional[int] = None, dry_run: bool = False) -> Dict:
        """Main classification process"""
        logger.info("Starting type classification process for animated videos")
        
        # Add TYPE column if needed
        if not self.add_type_column(dry_run):
            logger.error("Failed to add TYPE column to database")
            return {'error': 'Database schema update failed'}
        
        # Get videos to classify
        videos = self.get_videos_to_classify(limit)
        
        if not videos:
            logger.info("No animated videos found that need type classification")
            return {'message': 'No videos to classify'}
        
        logger.info(f"Found {len(videos)} animated videos to classify")
        
        # Process in batches
        total_results = {
            'total_videos': len(videos),
            'total_batches': 0,
            'total_success': 0,
            'total_errors': 0,
            'classifications': {}
        }
        
        for i in range(0, len(videos), self.batch_size):
            batch = videos[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            
            logger.info(f"Processing batch {batch_num} ({len(batch)} videos)")
            
            batch_results = self.classify_video_batch(batch, dry_run)
            
            # Aggregate results
            total_results['total_batches'] += 1
            total_results['total_success'] += batch_results['success']
            total_results['total_errors'] += batch_results['errors']
            
            # Merge classification counts
            for classification, count in batch_results['classifications'].items():
                total_results['classifications'][classification] = total_results['classifications'].get(classification, 0) + count
            
            logger.info(f"Batch {batch_num} completed: {batch_results['success']} success, {batch_results['errors']} errors")
            
            # Continue immediately to next batch for maximum speed
        
        # Final summary
        logger.info("🎉 Type classification completed!")
        logger.info(f"📊 Results: {total_results['total_success']} success, {total_results['total_errors']} errors")
        
        if total_results['classifications']:
            logger.info("📈 Classification breakdown:")
            for classification, count in total_results['classifications'].items():
                logger.info(f"   {classification}: {count}")
        
        return total_results

def main():
    parser = argparse.ArgumentParser(description='Type Classifier for Animated Videos')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of videos to process in each batch')
    parser.add_argument('--limit', type=int, help='Maximum number of videos to process')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    try:
        classifier = TypeClassifier(batch_size=args.batch_size)
        results = classifier.classify_videos(limit=args.limit, dry_run=args.dry_run)
        
        if 'error' in results:
            logger.error(f"Classification failed: {results['error']}")
            sys.exit(1)
        
        logger.info("Type classification process completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 