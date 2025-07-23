#!/usr/bin/env python3
"""
Video Reclassification Script

This script reclassifies videos in the database that are currently marked as animated.
It uses an improved prompt to better identify non-animated content and updates the database accordingly.

Usage:
    python reclassify_videos.py [--batch-size N] [--dry-run] [--limit N]
"""

import os
import sys
import logging
import argparse
import time
from datetime import datetime
from typing import List, Dict, Optional

import google.generativeai as genai
from dotenv import load_dotenv

# Import existing database and logging setup
from cloud_database import CloudDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'reclassification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VideoReclassifier:
    """Reclassifies videos using improved animation detection prompt"""
    
    def __init__(self):
        """Initialize the reclassifier"""
        # Setup Gemini AI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        # Setup database connection
        self.cloud_db = CloudDatabase()
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "reclassified_to_non_animated": 0,
            "reclassified_to_gameplay": 0,
            "remained_animated": 0,
            "errors": 0,
            "start_time": datetime.now()
        }
        
        logger.info("VideoReclassifier initialized successfully")
    
    def get_improved_prompt(self, video_data: Dict) -> str:
        """
        Create an improved prompt using video metadata.
        
        Args:
            video_data: Dictionary containing video metadata from database
            
        Returns:
            str: Enhanced prompt for better classification
        """
        
        # Extract metadata for context
        title = video_data.get('title', '')
        description = video_data.get('description', '')[:500]  # First 500 chars
        youtuber = video_data.get('youtuber', '')
        video_length = video_data.get('video_length', 0)
        url = video_data.get('url', '')
        
        # Convert seconds to readable format
        duration_minutes = int(video_length / 60) if video_length else 0
        
        # TODO: User will fill in this improved prompt
        # Placeholder prompt structure for now
        prompt = f"""
        RECLASSIFICATION TASK: Analyze this YouTube video and determine if it should remain classified as ANIMATED.

        VIDEO METADATA:
        - Title: {title}
        - Creator: {youtuber}
        - Duration: {duration_minutes} minutes
        - URL: {url}
        - Description: {description}

        Instruction:
        Analyze the provided YouTube video and its metadata and classify its primary format as exactly one of the following categories:
        ANIMATED, NOT_ANIMATED, GAMEPLAY

        Core Principle:
        Classification is based on the dominant visual medium and overall format. Evaluate what defines the viewer's primary experience: animated artistic content, filmed real-world/presenter-led content, or gameplay footage.

        Definitions and Criteria:

        ANIMATED
        Primary visuals consist of created artistic movement frame-by-frame, irrespective of whether narration or music overlays exist.
        Also include any review, analysis, essay, or commentary video whose primary subject matter is animated works, even if the presenter is on camera.

        Includes:
            •	Traditional 2D animation (cartoons, anime, hand-drawn shorts)
            •	3D/CGI animation (Pixar, DreamWorks, RWBY, Murder Drones)
            •	Motion graphics and infographic explainers (e.g., Kurzgesagt, The Infographics Show)
            •	Stop-motion (Wallace and Gromit, Coraline)
            •	Fully animated music videos (e.g., Gorillaz)
            •	Machinima: narrative, cinematic stories constructed inside game engines but directed like films (e.g., Red vs. Blue)
            •	Reviews, essays, commentary, or reactions where the primary subject is animated media (e.g., anime reviews, Pixar retrospectives)

        Excludes:
            •	Art tutorials, drawing demonstrations, speedpaints
            •	Presenter-led explainers that use animation as a supplement but are not about animation itself
            •	Gameplay recordings and commentary (even if the game itself is highly stylized or animated)

        NOT_ANIMATED
        Primary visuals consist of real-world footage or content where a person or avatar acts as a stand-in for a presenter/performer, and the subject matter is not animated media.

        Includes:
            •	Vlogs, tutorials, interviews, reviews about non-animated subjects
            •	VTuber streams and videos where the topic is not animated content
            •	Live-action documentaries, performances, music videos featuring real performers
            •	Reaction videos and commentary about non-animated content
            •	Video essays on real-world topics even if they include some animated visuals

        Excludes:
            •	Fully animated infographic videos (classified as ANIMATED)
            •	Machinima and narrative films constructed in game engines (classified as ANIMATED)
            •	Gameplay-driven content (classified as GAMEPLAY)

        GAMEPLAY
        Primary visuals consist of footage from the act of playing a video game, irrespective of art style or game aesthetics.

        Includes:
            •	Let's Plays and walkthroughs
            •	Gameplay streams and highlights
            •	Gameplay commentary where discussion overlays active game footage
            •	Gameplay compilations

        Excludes:
            •	Machinima and cinematic scenes shot in game engines (classified as ANIMATED)
            •	Video essays using gameplay footage as background visuals while discussing unrelated non-game topics (classified as NOT_ANIMATED)

        Additional Clarifications:
            •	Dominant Visual Test: If more than 80% of the video's runtime is defined by one visual format, classify accordingly.
            •	Mixed Content: For mixed-media videos, determine which visual format dominates across the core content—not intros or outros.
            •	Subject Matter Rule: Reviews, commentary, or essays about animated films/shows are classified as ANIMATED even if the visuals are presenter-led or include clips.
            •	Exclude gameplay-related videos regardless of how animated or cinematic the game is.

        Edge Case Examples:
            •	Amazing Digital Circus pilot → ANIMATED (Narrative, fully animated)
            •	Kurzgesagt explainer → ANIMATED (Infographic-driven animation)
            •	Elden Ring stream highlight → GAMEPLAY (Player actively playing game)
            •	Minecraft machinima film → ANIMATED (Narrative machinima ≠ gameplay)
            •	VTuber stream with animated avatar talking about anime → ANIMATED (Primary subject = animated content)
            •	VTuber stream playing Genshin Impact → GAMEPLAY (Primary activity = gameplay)
            •	Presenter reviewing Hazbin Hotel on camera → ANIMATED (Primary subject = animated content)
            •	Art speedpaint + commentary → NOT_ANIMATED (Tutorial/presentation format)

        RESPONSE FORMAT:
        You MUST respond with ONLY valid JSON in this exact format (no other text):
        {{
            "classification": "ANIMATED",
            "confidence": "HIGH",
            "reason": "Brief explanation"
        }}

        Replace "ANIMATED" with: ANIMATED, NOT_ANIMATED, GAMEPLAY, or ERROR
        Replace "HIGH" with: HIGH, MEDIUM, or LOW
        Replace "Brief explanation" with your reasoning

        JSON Response:
        """
        
        return prompt
    
    def classify_video(self, video_data: Dict) -> Dict:
        """
        Classify a single video using Gemini AI
        
        Args:
            video_data: Video metadata from database
            
        Returns:
            Dict: Classification result with reason
        """
        video_id = video_data.get('video_id')
        title = video_data.get('title', 'Unknown')
        
        try:
            logger.info(f"Classifying video: {video_id} - {title}")
            
            # Create improved prompt
            prompt = self.get_improved_prompt(video_data)
            
            # Call Gemini API with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(prompt)
                    raw_response = response.text.strip() if response.text else ""
                    
                    if raw_response:  # Got a non-empty response
                        break
                    else:
                        logger.warning(f"Empty response on attempt {attempt + 1} for {video_id}")
                        if attempt < max_retries - 1:
                            time.sleep(3)  # Wait longer between retries
                            continue
                        
                except Exception as api_error:
                    logger.warning(f"API error on attempt {attempt + 1} for {video_id}: {str(api_error)}")
                    if attempt < max_retries - 1:
                        time.sleep(3)
                        continue
                    else:
                        raise api_error
            
            logger.info(f"Gemini raw response for {video_id}: '{raw_response}'")
            
            # Check for empty response
            if not raw_response:
                logger.warning(f"Empty response from Gemini for {video_id}")
                return {
                    "classification": "ERROR",
                    "confidence": "NONE",
                    "reason": "Empty response from Gemini API",
                    "raw_response": ""
                }
            
            # Try to parse JSON response
            try:
                import json
                classification_data = json.loads(raw_response)
                
                classification = classification_data.get('classification', '').upper()
                confidence = classification_data.get('confidence', 'UNKNOWN')
                reason = classification_data.get('reason', 'No reason provided')
                
            except (json.JSONDecodeError, KeyError) as e:
                # Fallback to simple text parsing if JSON fails
                logger.warning(f"JSON parsing failed for {video_id}, using fallback: {str(e)}")
                logger.warning(f"Raw response that failed: '{raw_response}'")
                
                # More robust text parsing
                response_upper = raw_response.upper()
                
                # Look for clear classification patterns
                if any(phrase in response_upper for phrase in ["NOT_ANIMATED", "NOT ANIMATED", "LIVE-ACTION", "LIVE ACTION"]):
                    classification = "NOT_ANIMATED"
                    reason = f"Text parsing detected non-animated content: {raw_response[:100]}"
                elif "GAMEPLAY" in response_upper:
                    classification = "GAMEPLAY" 
                    reason = f"Text parsing detected gameplay content: {raw_response[:100]}"
                elif any(phrase in response_upper for phrase in ["ANIMATED", "ANIMATION"]):
                    classification = "ANIMATED"
                    reason = f"Text parsing detected animated content: {raw_response[:100]}"
                elif "ERROR" in response_upper:
                    classification = "ERROR"
                    reason = f"Error indicated in response: {raw_response[:100]}"
                else:
                    # If we can't parse anything meaningful, classify as error
                    classification = "ERROR"
                    reason = f"Could not parse response: {raw_response[:100]}"
                    logger.error(f"Unparseable response for {video_id}: '{raw_response}'")
                
                confidence = "LOW"
            
            return {
                "classification": classification,
                "confidence": confidence,
                "reason": reason,
                "raw_response": raw_response
            }
            
        except Exception as e:
            logger.error(f"Error classifying video {video_id}: {str(e)}")
            return {
                "classification": "ERROR",
                "confidence": "NONE",
                "reason": f"Classification error: {str(e)}",
                "raw_response": ""
            }
    
    def get_videos_to_reclassify(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get videos from database that are currently marked as animated
        
        Args:
            limit: Optional limit on number of videos to fetch
            
        Returns:
            List[Dict]: List of video metadata dictionaries
        """
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Query for videos marked as animated
                query = """
                    SELECT video_id, title, url, youtuber, description, 
                           video_length, views, discovered_at
                    FROM videos_full 
                    WHERE is_animated = true
                    ORDER BY discovered_at DESC
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
                
                logger.info(f"Found {len(videos)} videos marked as animated")
                return videos
                
        except Exception as e:
            logger.error(f"Error fetching videos from database: {str(e)}")
            return []
    
    def update_video_classification(self, video_id: str, is_animated: bool, 
                                  classification_reason: str, dry_run: bool = False) -> bool:
        """
        Update video classification in database
        
        Args:
            video_id: Video ID to update
            is_animated: New animated status
            classification_reason: Reason for the classification
            dry_run: If True, don't actually update database
            
        Returns:
            bool: True if successful, False otherwise
        """
        if dry_run:
            logger.info(f"DRY RUN: Would update {video_id} to is_animated={is_animated}")
            return True
        
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update the video
                cursor.execute("""
                    UPDATE videos_full 
                    SET is_animated = %s
                    WHERE video_id = %s
                """, (is_animated, video_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Updated {video_id}: is_animated={is_animated}")
                    return True
                else:
                    logger.warning(f"No rows updated for video_id: {video_id}")
                    return False
                
        except Exception as e:
            logger.error(f"Error updating video {video_id}: {str(e)}")
            return False
    
    def reclassify_batch(self, videos: List[Dict], dry_run: bool = False) -> None:
        """
        Reclassify a batch of videos
        
        Args:
            videos: List of video metadata dictionaries
            dry_run: If True, don't update database
        """
        for i, video in enumerate(videos, 1):
            video_id = video.get('video_id')
            title = video.get('title', 'Unknown')
            
            logger.info(f"Processing {i}/{len(videos)}: {video_id} - {title}")
            
            try:
                # Classify the video
                result = self.classify_video(video)
                classification = result.get('classification')
                reason = result.get('reason', '')
                confidence = result.get('confidence', '')
                
                self.stats["total_processed"] += 1
                
                if classification == "NOT_ANIMATED":
                    # Video should be marked as non-animated
                    logger.info(f"RECLASSIFIED as NOT_ANIMATED: {video_id}")
                    logger.info(f"Reason: {reason}")
                    logger.info(f"Confidence: {confidence}")
                    
                    # Update database
                    if self.update_video_classification(video_id, False, reason, dry_run):
                        self.stats["reclassified_to_non_animated"] += 1
                    else:
                        self.stats["errors"] += 1
                        
                elif classification == "GAMEPLAY":
                    # Video should be marked as non-animated (gameplay)
                    logger.info(f"RECLASSIFIED as GAMEPLAY: {video_id}")
                    logger.info(f"Reason: {reason}")
                    logger.info(f"Confidence: {confidence}")
                    
                    # Update database
                    if self.update_video_classification(video_id, False, reason, dry_run):
                        self.stats["reclassified_to_gameplay"] += 1
                    else:
                        self.stats["errors"] += 1
                        
                elif classification == "ANIMATED":
                    # Video remains animated
                    logger.info(f"CONFIRMED as ANIMATED: {video_id}")
                    self.stats["remained_animated"] += 1
                    
                else:
                    # Error or unknown classification
                    logger.error(f"UNKNOWN classification for {video_id}: {classification}")
                    logger.error(f"Reason: {reason}")
                    self.stats["errors"] += 1
                
                # Longer delay to avoid rate limiting and empty responses
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing video {video_id}: {str(e)}")
                self.stats["errors"] += 1
                
            # Print progress every 10 videos
            if i % 10 == 0:
                self.print_progress()
    
    def print_progress(self) -> None:
        """Print current progress statistics"""
        elapsed = datetime.now() - self.stats["start_time"]
        
        logger.info("="*50)
        logger.info("RECLASSIFICATION PROGRESS")
        logger.info("="*50)
        logger.info(f"Total processed: {self.stats['total_processed']}")
        logger.info(f"Reclassified to NOT_ANIMATED: {self.stats['reclassified_to_non_animated']}")
        logger.info(f"Reclassified to GAMEPLAY: {self.stats['reclassified_to_gameplay']}")
        logger.info(f"Remained animated: {self.stats['remained_animated']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Elapsed time: {elapsed}")
        logger.info("="*50)
    
    def print_final_summary(self) -> None:
        """Print final summary of reclassification"""
        elapsed = datetime.now() - self.stats["start_time"]
        
        logger.info("="*60)
        logger.info("🎬 RECLASSIFICATION COMPLETE")
        logger.info("="*60)
        logger.info(f"📊 FINAL STATISTICS:")
        logger.info(f"   • Total videos processed: {self.stats['total_processed']}")
        logger.info(f"   • Reclassified to NOT_ANIMATED: {self.stats['reclassified_to_non_animated']}")
        logger.info(f"   • Reclassified to GAMEPLAY: {self.stats['reclassified_to_gameplay']}")
        logger.info(f"   • Remained animated: {self.stats['remained_animated']}")
        logger.info(f"   • Errors encountered: {self.stats['errors']}")
        logger.info(f"   • Total elapsed time: {elapsed}")
        
        if self.stats['total_processed'] > 0:
            total_reclassified = self.stats['reclassified_to_non_animated'] + self.stats['reclassified_to_gameplay']
            accuracy = (total_reclassified + self.stats['remained_animated']) / self.stats['total_processed'] * 100
            logger.info(f"   • Success rate: {accuracy:.1f}%")
            
            if total_reclassified > 0:
                reclassification_rate = total_reclassified / self.stats['total_processed'] * 100
                logger.info(f"   • Reclassification rate: {reclassification_rate:.1f}%")
        
        logger.info("="*60)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Reclassify YouTube videos in database")
    parser.add_argument("--batch-size", type=int, default=50, 
                       help="Number of videos to process in one batch (default: 50)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Don't update database, just show what would be changed")
    parser.add_argument("--limit", type=int, 
                       help="Limit total number of videos to process")
    
    args = parser.parse_args()
    
    logger.info("🎬 Starting Video Reclassification Script")
    logger.info("="*50)
    
    if args.dry_run:
        logger.info("⚠️  DRY RUN MODE - No database updates will be made")
    
    try:
        # Initialize reclassifier
        reclassifier = VideoReclassifier()
        
        # Get videos to reclassify
        logger.info("Fetching videos from database...")
        videos = reclassifier.get_videos_to_reclassify(limit=args.limit)
        
        if not videos:
            logger.info("No videos found to reclassify")
            return
        
        logger.info(f"Found {len(videos)} videos to reclassify")
        
        # Process in batches
        batch_size = args.batch_size
        total_batches = (len(videos) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(videos))
            batch = videos[start_idx:end_idx]
            
            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} videos)")
            
            reclassifier.reclassify_batch(batch, dry_run=args.dry_run)
            
            # Progress update
            reclassifier.print_progress()
        
        # Final summary
        reclassifier.print_final_summary()
        
    except KeyboardInterrupt:
        logger.info("Reclassification interrupted by user")
    except Exception as e:
        logger.error(f"Reclassification failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()