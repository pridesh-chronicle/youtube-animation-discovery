import json
import time
import sqlite3
import logging
import os
from api_client import BrightDataClient, BrightDataTimeoutError, BrightDataAPIError
from animation_detector import is_animated
from cloud_database import CloudDatabase
from cloud_storage import CloudStorage
from discovery_queue import DiscoveryQueue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discovery_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscoveryAgent:
    def __init__(self, save_videos=False, save_frames=False):
        self.client = BrightDataClient()
        self.processed_videos = set()  # Global set to track processed videos
        self.animated_videos = []      # Store animated videos found
        
        self.save_videos = save_videos
        self.save_frames = save_frames

        self.cloud_db = CloudDatabase()
        self.cloud_storage = CloudStorage()
        
        # Initialize cloud-based queue
        self.queue = DiscoveryQueue(self.cloud_db.get_connection)
        
        # Initialize database
        self.setup_database()
        
        logger.info("Discovery agent initialized with cloud queue", extra={
            "save_videos": save_videos,
            "save_frames": save_frames
        })
    
    def is_already_processed(self, video_id):
        """Check if video already exists in database"""
        try:
            with self.cloud_db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM videos_full WHERE video_id = %s LIMIT 1", (video_id,))
                exists = cursor.fetchone() is not None
                
                if exists:
                    logger.debug("Video already in database", extra={"video_id": video_id})
                
                return exists
        except Exception as e:
            logger.error("Failed to check duplicate", extra={
                "video_id": video_id,
                "error": str(e)
            })
            return False
    
    def add_to_queue(self, video_ids, source_video_id=None):
        """Add video IDs to cloud queue if not already processed"""
        if not video_ids:
            return
            
        # Filter out already processed videos
        filtered_video_ids = []
        for video_id in video_ids:
            if video_id in self.processed_videos:
                logger.debug("Video already processed in session", extra={"video_id": video_id})
                continue
                
            # Check database for duplicates
            if self.is_already_processed(video_id):
                self.processed_videos.add(video_id)  # Mark as processed to avoid future checks
                continue
                
            filtered_video_ids.append(video_id)
        
        if filtered_video_ids:
            # Add to cloud queue
            added_count = self.queue.add_videos(filtered_video_ids, source_video_id)
            
            logger.info("Videos added to cloud queue", extra={
                "added_to_queue": added_count,
                "total_requested": len(video_ids),
                "filtered_count": len(filtered_video_ids),
                "source_video": source_video_id
            })
        else:
            logger.debug("No new videos to add to queue")
    
    def process_video_batch(self, batch_size=10, max_retries=2):
        """Process a batch of videos from the cloud queue with retry logic"""
        # Get batch from cloud queue
        batch = self.queue.get_next_batch(batch_size)
        
        if not batch:
            logger.debug("No videos in queue to process")
            return False
        
        # Convert to URLs
        video_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in batch]
        video_data_list = None
        
        # Retry logic for API calls
        for attempt in range(max_retries + 1):
            try:
                logger.info("Processing video batch", extra={
                    "batch_size": len(batch),
                    "remaining_in_queue": len(self.queue),
                    "video_ids": batch,
                    "attempt": attempt + 1,
                    "max_attempts": max_retries + 1
                })
                
                # Fetch data with timeout handling
                video_data_list = self.client.fetch_videos(video_urls)
                
                if not video_data_list:
                    raise BrightDataAPIError("No video data returned from API")
                
                # Success - break out of retry loop
                logger.info("Successfully fetched video data", extra={
                    "batch_size": len(batch),
                    "data_count": len(video_data_list),
                    "attempt": attempt + 1
                })
                break
                
            except BrightDataTimeoutError as e:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 30  # 30s, 60s, etc.
                    logger.warning("BrightData API timeout - retrying", extra={
                        "batch_size": len(batch),
                        "attempt": attempt + 1,
                        "max_attempts": max_retries + 1,
                        "wait_time": wait_time,
                        "error": str(e)
                    })
                    time.sleep(wait_time)
                else:
                    logger.warning("Max retries exceeded due to timeout - skipping batch", extra={
                        "batch_size": len(batch),
                        "video_ids": batch,
                        "max_retries": max_retries,
                        "error": str(e)
                    })
                    # Mark these videos as failed in cloud queue
                    self.queue.mark_failed(batch, f"Timeout after {max_retries} retries: {str(e)}")
                    return True  # Continue processing other batches
                    
            except Exception as e:
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 15  # Shorter wait for general errors
                    logger.warning("API error - retrying", extra={
                        "batch_size": len(batch),
                        "attempt": attempt + 1,
                        "max_attempts": max_retries + 1,
                        "wait_time": wait_time,
                        "error": str(e)
                    })
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded due to API error - skipping batch", extra={
                        "batch_size": len(batch),
                        "video_ids": batch,
                        "max_retries": max_retries,
                        "error": str(e)
                    })
                    # Mark these videos as failed in cloud queue
                    self.queue.mark_failed(batch, f"API error after {max_retries} retries: {str(e)}")
                    return True  # Continue processing other batches
        
        # If we get here without video_data_list, something went wrong
        if not video_data_list:
            logger.error("Failed to get video data after all retries", extra={
                "batch_size": len(batch),
                "video_ids": batch
            })
            # Mark as failed in cloud queue and continue
            self.queue.mark_failed(batch, "Failed to get video data after all retries")
            return True
        
        batch_stats = {
            "animated_found": 0,
            "non_animated": 0,
            "processing_errors": 0,
            "total_recommendations": 0
        }
        
        processed_video_ids = []  # Track successfully processed videos for cloud queue
        
        for video_data in video_data_list:
            video_id = video_data.get('video_id')
            video_url = video_data.get('url')
            video_title = video_data.get('title', 'Unknown')
            
            logger.info("Processing individual video", extra={
                "video_id": video_id,
                "title": video_title,
                "views": video_data.get('views'),
                "channel": video_data.get('youtuber')
            })
            
            # Mark as processed in memory
            self.processed_videos.add(video_id)
            
            try:
                # Check if animated
                result = is_animated(video_url, save_videos=self.save_videos, save_frames=self.save_frames)

                if isinstance(result, tuple):
                    is_animated_result, video_path, _ = result
                else:
                    is_animated_result = result
                    video_path = None

                if is_animated_result:
                    logger.info("Animated video found", extra={
                        "video_id": video_id,
                        "title": video_title,
                        "views": video_data.get('views'),
                        "channel": video_data.get('youtuber')
                    })
                    
                    self.animated_videos.append(video_data)
                    batch_stats["animated_found"] += 1
                    
                    # Upload video to cloud storage (no frames)
                    video_cloud_url = None
                    
                    if video_path and self.cloud_storage:
                        video_cloud_url = self.cloud_storage.upload_video(video_path, video_id)
                    
                    # Save with cloud URL (no frames)
                    self.save_to_cloud_db(video_data, video_cloud_url)
                    
                    # Get recommendations and add to queue
                    recommendations = self.client.get_recommendations(video_data)
                    batch_stats["total_recommendations"] += len(recommendations)
                    
                    logger.info("Found recommendations", extra={
                        "video_id": video_id,
                        "recommendation_count": len(recommendations),
                        "sample_recommendations": recommendations[:3] if recommendations else []
                    })
                    
                    self.add_to_queue(recommendations, source_video_id=video_id)
                else:
                    logger.info("Non-animated video", extra={
                        "video_id": video_id,
                        "title": video_title
                    })
                    batch_stats["non_animated"] += 1
                
                # Mark video as successfully processed for cloud queue
                processed_video_ids.append(video_id)
                    
            except Exception as e:
                logger.error("Error processing video", extra={
                    "video_id": video_id,
                    "title": video_title,
                    "error": str(e)
                })
                batch_stats["processing_errors"] += 1
                # Don't add to processed_video_ids if there was an error
        
        # Mark successfully processed videos as completed in cloud queue
        if processed_video_ids:
            self.queue.mark_completed(processed_video_ids)
        
        # Get queue stats for logging
        queue_stats = self.queue.get_stats()
        
        # Log batch summary
        logger.info("Batch processing completed", extra={
            "batch_stats": batch_stats,
            "total_animated_found": len(self.animated_videos),
            "total_processed": len(self.processed_videos),
            "cloud_queue_stats": queue_stats
        })
        
        return True
    
    def start_discovery(self, seed_video_ids):
        """Start the discovery process - runs until queue is empty"""
        logger.info("Starting discovery process", extra={
            "seed_video_count": len(seed_video_ids),
            "seed_videos": seed_video_ids,
            "mode": "run_until_queue_empty"
        })
        
        # Add seed videos to queue
        self.add_to_queue(seed_video_ids)
        
        # Process videos until queue is empty
        iteration = 0
        while True:  # Continue until no more videos to process
            # Check if there are videos in the queue
            queue_stats = self.queue.get_stats()
            if queue_stats.get('pending', 0) == 0:
                logger.info("No pending videos in queue, stopping discovery")
                break
                
            iteration += 1
            iteration_start_time = time.time()
            
            logger.info("Starting iteration", extra={
                "iteration": iteration,
                "queue_stats": queue_stats,
                "total_processed": len(self.processed_videos),
                "animated_found": len(self.animated_videos)
            })
            
            if not self.process_video_batch():
                logger.info("No videos processed in batch, stopping discovery", extra={
                    "final_iteration": iteration,
                    "total_animated_found": len(self.animated_videos),
                    "total_processed": len(self.processed_videos)
                })
                break
            
            iteration_time = time.time() - iteration_start_time
            
            # Get updated queue stats
            current_queue_stats = self.queue.get_stats()
            
            logger.info("Iteration completed", extra={
                "iteration": iteration,
                "duration_seconds": round(iteration_time, 2),
                "cumulative_animated": len(self.animated_videos),
                "queue_stats": current_queue_stats
            })
            
            # Process immediately for maximum speed
        
        # Final summary with queue cleanup
        final_queue_stats = self.queue.get_stats()
        
        logger.info("Discovery process completed", extra={
            "total_iterations": iteration,
            "total_animated_videos": len(self.animated_videos),
            "total_videos_processed": len(self.processed_videos),
            "final_queue_stats": final_queue_stats,
            "completion_reason": "queue_empty"
        })
        
        return self.animated_videos
    
    def setup_database(self):
        logger.info("Setting up database connection")
        self.cloud_db.setup_database()
        logger.info("Database setup completed")
    
    def save_to_cloud_db(self, video_data, video_cloud_url=None):
        video_id = video_data.get('video_id')
        try:
            recommendations = self.client.get_recommendations(video_data)
            video_data['num_recommendations'] = len(recommendations)

            self.cloud_db.save_video(video_data, video_cloud_url)
            
            logger.info("Video saved to database", extra={
                "video_id": video_id,
                "title": video_data.get('title'),
                "has_cloud_url": bool(video_cloud_url),
                "recommendation_count": len(recommendations)
            })

            if video_cloud_url:
                logger.info("Video uploaded to cloud storage", extra={
                    "video_id": video_id,
                    "cloud_url": video_cloud_url
                })

        except Exception as e:
            logger.error("Failed to save video to database", extra={
                "video_id": video_id,
                "title": video_data.get('title'),
                "error": str(e)
            })
    
    def save_results(self, filename="animated_videos.json"):
        """Save discovered animated videos to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.animated_videos, f, indent=2)
            
            logger.info("Results saved to file", extra={
                "output_file": filename,
                "video_count": len(self.animated_videos),
                "file_size_mb": round(os.path.getsize(filename) / (1024*1024), 2)
            })
        except Exception as e:
            logger.error("Failed to save results to file", extra={
                "output_file": filename,
                "error": str(e)
            }) 