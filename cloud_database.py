import os
import psycopg2
import sqlalchemy
import logging
from contextlib import contextmanager

# Configure logging for database operations
logger = logging.getLogger(__name__)

class CloudDatabase:
    def __init__(self):
        self.connection_string = self._build_connection_string()
        logger.info("Cloud database client initialized")
        
    def _build_connection_string(self):
        """Build PostgreSQL connection string"""
        return f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    
    @contextmanager
    def get_connection(self):
        """Get database connection context manager"""
        try:
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                port=5432
            )
            logger.debug("Database connection established")
            yield conn
        except Exception as e:
            logger.error("Database connection failed", extra={"error": str(e)})
            raise
        finally:
            try:
                conn.close()
                logger.debug("Database connection closed")
            except:
                pass

    def setup_database(self):
        """Create tables in Cloud SQL"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS videos (
                        video_id TEXT PRIMARY KEY,
                        title TEXT,
                        url TEXT,
                        views BIGINT,
                        likes INTEGER,
                        num_comments INTEGER,
                        subscribers BIGINT,
                        video_length INTEGER,
                        date_posted TIMESTAMP,
                        youtuber TEXT,
                        handle_name TEXT,
                        channel_url TEXT,
                        description TEXT,
                        quality_label TEXT,
                        verified BOOLEAN,
                        num_recommendations INTEGER,
                        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        video_cloud_url TEXT
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_discovered_at ON videos(discovered_at);
                    CREATE INDEX IF NOT EXISTS idx_youtuber ON videos(youtuber);
                    CREATE INDEX IF NOT EXISTS idx_views ON videos(views);
                """)
                conn.commit()
                
                # Check if table exists and get count
                cursor.execute("SELECT COUNT(*) FROM videos")
                existing_count = cursor.fetchone()[0]
                
                logger.info("Database setup completed", extra={
                    "existing_videos": existing_count
                })
                
        except Exception as e:
            logger.error("Database setup failed", extra={"error": str(e)})
            raise

    def save_video(self, video_data, video_cloud_url=None):
        """Save video to Cloud SQL"""
        video_id = video_data.get('video_id')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if video already exists
                cursor.execute("SELECT 1 FROM videos WHERE video_id = %s", (video_id,))
                is_update = cursor.fetchone() is not None
                
                cursor.execute("""
                    INSERT INTO videos (
                        video_id, title, url, views, likes, num_comments, subscribers,
                        video_length, date_posted, youtuber, handle_name, channel_url,
                        description, quality_label, verified, num_recommendations,
                        video_cloud_url
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (video_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        views = EXCLUDED.views,
                        likes = EXCLUDED.likes,
                        video_cloud_url = EXCLUDED.video_cloud_url
                """, (
                    video_data.get('video_id'),
                    video_data.get('title'),
                    video_data.get('url'),
                    video_data.get('views'),
                    video_data.get('likes'),
                    video_data.get('num_comments'),
                    video_data.get('subscribers'),
                    video_data.get('video_length'),
                    video_data.get('date_posted'),
                    video_data.get('youtuber'),
                    video_data.get('handle_name'),
                    video_data.get('channel_url'),
                    (video_data.get('description', '') or '')[:500],
                    video_data.get('quality_label'),
                    video_data.get('verified'),
                    0,  # num_recommendations will be updated separately
                    video_cloud_url
                ))
                conn.commit()
                
                action = "Updated" if is_update else "Inserted"
                logger.info(f"Video {action.lower()} in database", extra={
                    "video_id": video_id,
                    "action": action,
                    "title": video_data.get('title'),
                    "has_cloud_url": bool(video_cloud_url)
                })
                
        except Exception as e:
            logger.error("Failed to save video to database", extra={
                "video_id": video_id,
                "error": str(e)
            })
            raise