import logging
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

class DiscoveryQueue:
    """Simplified cloud-based discovery queue using PostgreSQL"""
    
    def __init__(self, db_connection_func):
        """Initialize with database connection function"""
        self.get_connection = db_connection_func
        self.setup_table()
        logger.info("DiscoveryQueue initialized")
    
    def setup_table(self):
        """Create the discovery queue table if it doesn't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS discovery_queue (
                        id SERIAL PRIMARY KEY,
                        video_id TEXT UNIQUE NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source_video_id TEXT,
                        status TEXT DEFAULT 'pending',
                        retry_count INTEGER DEFAULT 0,
                        error_message TEXT,
                        processed_at TIMESTAMP,
                        
                        CONSTRAINT unique_video_id UNIQUE (video_id)
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_queue_status ON discovery_queue(status);
                    CREATE INDEX IF NOT EXISTS idx_queue_added_at ON discovery_queue(added_at);
                """)
                conn.commit()
                logger.info("Discovery queue table setup completed")
        except Exception as e:
            logger.error(f"Failed to setup queue table: {str(e)}")
            raise
    
    def add_videos(self, video_ids: List[str], source_video_id: Optional[str] = None) -> int:
        """Add videos to the queue"""
        if not video_ids:
            return 0
            
        added_count = 0
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for video_id in video_ids:
                    try:
                        cursor.execute("""
                            INSERT INTO discovery_queue (video_id, source_video_id)
                            VALUES (%s, %s)
                            ON CONFLICT (video_id) DO NOTHING
                        """, (video_id, source_video_id))
                        
                        if cursor.rowcount > 0:
                            added_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Failed to add video {video_id}: {str(e)}")
                        continue
                
                conn.commit()
                logger.info(f"Added {added_count}/{len(video_ids)} videos to queue")
                
        except Exception as e:
            logger.error(f"Failed to add videos to queue: {str(e)}")
            raise
        
        return added_count
    
    def get_next_batch(self, batch_size: int = 10) -> List[str]:
        """Get next batch of videos to process"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT video_id FROM discovery_queue 
                    WHERE status = 'pending' 
                    ORDER BY added_at ASC 
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                """, (batch_size,))
                
                video_ids = [row[0] for row in cursor.fetchall()]
                
                if video_ids:
                    cursor.execute("""
                        UPDATE discovery_queue 
                        SET status = 'processing'
                        WHERE video_id = ANY(%s)
                    """, (video_ids,))
                    
                    conn.commit()
                    logger.info(f"Retrieved {len(video_ids)} videos from queue")
                
                return video_ids
                
        except Exception as e:
            logger.error(f"Failed to get next batch: {str(e)}")
            return []
    
    def mark_completed(self, video_ids: List[str]):
        """Mark videos as successfully processed"""
        if not video_ids:
            return
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE discovery_queue 
                    SET status = 'completed', processed_at = CURRENT_TIMESTAMP
                    WHERE video_id = ANY(%s)
                """, (video_ids,))
                conn.commit()
                
                logger.info(f"Marked {cursor.rowcount} videos as completed")
                
        except Exception as e:
            logger.error(f"Failed to mark videos as completed: {str(e)}")
    
    def mark_failed(self, video_ids: List[str], error_message: str = None):
        """Mark videos as failed (will retry later)"""
        if not video_ids:
            return
            
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE discovery_queue 
                    SET status = 'pending', 
                        retry_count = retry_count + 1,
                        error_message = %s
                    WHERE video_id = ANY(%s)
                """, (error_message, video_ids))
                conn.commit()
                
                logger.warning(f"Marked {cursor.rowcount} videos as failed (will retry)")
                
        except Exception as e:
            logger.error(f"Failed to mark videos as failed: {str(e)}")
    
    def get_stats(self) -> dict:
        """Get queue statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT status, COUNT(*) as count 
                    FROM discovery_queue 
                    GROUP BY status
                """)
                status_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                cursor.execute("SELECT COUNT(*) FROM discovery_queue")
                total_count = cursor.fetchone()[0]
                
                return {
                    "total": total_count,
                    "pending": status_counts.get('pending', 0),
                    "processing": status_counts.get('processing', 0),
                    "completed": status_counts.get('completed', 0),
                    "failed": status_counts.get('failed', 0)
                }
                
        except Exception as e:
            logger.error(f"Failed to get queue stats: {str(e)}")
            return {}
    
    def cleanup_old_completed(self, days_old: int = 7) -> int:
        """Clean up old completed entries"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM discovery_queue 
                    WHERE status = 'completed' 
                    AND processed_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days_old,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old completed entries")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old entries: {str(e)}")
            return 0