import os
import psycopg2
from psycopg2 import pool
import sqlalchemy
import logging
from contextlib import contextmanager
import threading

# Configure logging for database operations
logger = logging.getLogger(__name__)

class CloudDatabase:
    def __init__(self):
        self.connection_string = self._build_connection_string()
        self._connection_pool = None
        self._pool_lock = threading.Lock()
        self._initialize_connection_pool()
        logger.info("Cloud database client initialized with connection pool")
        
    def _build_connection_string(self):
        """Build PostgreSQL connection string"""
        return f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    
    def _initialize_connection_pool(self):
        """Initialize connection pool with proper limits"""
        try:
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,      # Minimum connections in pool
                maxconn=10,     # Maximum connections in pool  
                host=os.getenv('DB_HOST'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                port=5432
            )
            logger.info("Database connection pool initialized (1-10 connections)")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection from pool"""
        conn = None
        try:
            # Get connection from pool (thread-safe)
            conn = self._connection_pool.getconn()
            if conn:
                logger.debug("Database connection acquired from pool")
                yield conn
            else:
                raise Exception("Failed to get connection from pool")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            logger.error(f"Connection details - Host: {os.getenv('DB_HOST')}, DB: {os.getenv('DB_NAME')}, User: {os.getenv('DB_USER')}")
            raise
        finally:
            # Return connection to pool
            if conn:
                try:
                    self._connection_pool.putconn(conn)
                    logger.debug("Database connection returned to pool")
                except Exception as e:
                    logger.error(f"Failed to return connection to pool: {str(e)}")

    def close_pool(self):
        """Close all connections in the pool"""
        try:
            if self._connection_pool:
                self._connection_pool.closeall()
                logger.info("Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing connection pool: {str(e)}")

    def setup_database(self):
        """Create tables in Cloud SQL with comprehensive BrightData schema"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS videos_full (
                        -- Basic Video Information
                        video_id TEXT PRIMARY KEY,
                        title TEXT,
                        url TEXT,
                        video_length INTEGER,
                        upload_date TIMESTAMP,
                        date_posted TIMESTAMP,
                        
                        -- Channel Information
                        youtuber TEXT,
                        handle_name TEXT,
                        channel_url TEXT,
                        channel_id TEXT,
                        verified BOOLEAN,
                        
                        -- Engagement Metrics
                        views BIGINT,
                        likes INTEGER,
                        dislikes INTEGER,
                        num_comments INTEGER,
                        subscribers BIGINT,
                        
                        -- Content Details
                        description TEXT,
                        category TEXT,
                        tags JSONB,
                        hashtags JSONB,
                        language TEXT,
                        
                        -- Technical Details
                        quality_label TEXT,
                        fps INTEGER,
                        codecs JSONB,
                        formats JSONB,
                        thumbnails JSONB,
                        captions JSONB,
                        
                        -- Transcript Data
                        formatted_transcript JSONB,
                        transcript_text TEXT,
                        
                        -- Recommendations & Related
                        recommended_videos JSONB,
                        next_recommended_videos JSONB,
                        related_videos JSONB,
                        
                        -- Live Stream Data
                        is_live BOOLEAN,
                        was_live BOOLEAN,
                        live_start_time TIMESTAMP,
                        live_end_time TIMESTAMP,
                        concurrent_viewers INTEGER,
                        
                        -- Age & Restrictions
                        age_limit INTEGER,
                        is_family_friendly BOOLEAN,
                        content_rating TEXT,
                        
                        -- Monetization
                        is_monetized BOOLEAN,
                        has_ads BOOLEAN,
                        
                        -- Performance Metrics
                        view_count_24h INTEGER,
                        like_ratio FLOAT,
                        engagement_rate FLOAT,
                        
                        -- Geographic Data
                        country TEXT,
                        region TEXT,
                        
                        -- Video Analysis
                        duration_category TEXT,
                        content_type TEXT,
                        
                        -- Enhanced BrightData Fields (collected during discovery)
                        music TEXT,
                        preview_image TEXT,
                        shortcode TEXT,
                        avatar_img_channel TEXT,
                        is_sponsored BOOLEAN,
                        license TEXT,
                        viewport_frames JSONB,
                        current_optimal_res TEXT,
                        color TEXT,
                        quality TEXT,
                        post_type TEXT,
                        youtuber_id TEXT,
                        transcript JSONB,
                        transcript_language TEXT,
                        chapters JSONB,
                        
                        -- Discovery Agent Fields
                        num_recommendations INTEGER,
                        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        video_cloud_url TEXT,
                        is_animated BOOLEAN DEFAULT TRUE
                    );
                    
                    -- Create comprehensive indexes
                    CREATE INDEX IF NOT EXISTS idx_discovered_at ON videos_full(discovered_at);
                    CREATE INDEX IF NOT EXISTS idx_youtuber ON videos_full(youtuber);
                    CREATE INDEX IF NOT EXISTS idx_views ON videos_full(views);
                    CREATE INDEX IF NOT EXISTS idx_upload_date ON videos_full(upload_date);
                    CREATE INDEX IF NOT EXISTS idx_category ON videos_full(category);
                    CREATE INDEX IF NOT EXISTS idx_language ON videos_full(language);
                    CREATE INDEX IF NOT EXISTS idx_is_animated ON videos_full(is_animated);
                    
                    -- JSONB indexes for complex queries
                    CREATE INDEX IF NOT EXISTS idx_tags_gin ON videos_full USING gin(tags);
                    CREATE INDEX IF NOT EXISTS idx_hashtags_gin ON videos_full USING gin(hashtags);
                    CREATE INDEX IF NOT EXISTS idx_recommended_videos_gin ON videos_full USING gin(recommended_videos);
                """)
                conn.commit()
                
                # Check if table exists and get count
                cursor.execute("SELECT COUNT(*) FROM videos_full")
                existing_count = cursor.fetchone()[0]
                
                logger.info("Comprehensive database setup completed", extra={
                    "table": "videos_full",
                    "existing_videos": existing_count,
                    "schema": "comprehensive_brightdata"
                })
                
        except Exception as e:
            logger.error("Database setup failed", extra={"error": str(e)})
            raise

    def save_video(self, video_data, video_cloud_url=None):
        """Save comprehensive video data to Cloud SQL"""
        import json
        
        video_id = video_data.get('video_id')
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if video already exists
                cursor.execute("SELECT 1 FROM videos_full WHERE video_id = %s", (video_id,))
                is_update = cursor.fetchone() is not None
                
                # Helper function to safely convert to JSON
                def to_json(data):
                    if data is None:
                        return None
                    # Always ensure valid JSON format
                    try:
                        return json.dumps(data, ensure_ascii=False, default=str)
                    except (TypeError, ValueError):
                        # If it can't be serialized, convert to string and then to JSON
                        return json.dumps(str(data))
                
                # Helper function to safely extract fields
                def safe_extract(field_name, force_json=False):
                    value = video_data.get(field_name)
                    if value is None:
                        return None
                    if force_json or isinstance(value, (dict, list)):
                        return to_json(value)
                    return value
                
                # Prepare data with all BrightData fields (including new enhancement fields)
                cursor.execute("""
                    INSERT INTO videos_full (
                        video_id, title, url, video_length, upload_date, date_posted,
                        youtuber, handle_name, channel_url, channel_id, verified,
                        views, likes, dislikes, num_comments, subscribers,
                        description, category, tags, hashtags, language,
                        quality_label, fps, codecs, formats, thumbnails, captions,
                        formatted_transcript, transcript_text,
                        recommended_videos, next_recommended_videos, related_videos,
                        is_live, was_live, live_start_time, live_end_time, concurrent_viewers,
                        age_limit, is_family_friendly, content_rating,
                        is_monetized, has_ads,
                        view_count_24h, like_ratio, engagement_rate,
                        country, region,
                        duration_category, content_type,
                        music, preview_image, shortcode, avatar_img_channel, is_sponsored,
                        license, viewport_frames, current_optimal_res, color, quality,
                        post_type, youtuber_id, transcript, transcript_language, chapters,
                        num_recommendations, video_cloud_url, is_animated
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (video_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        views = EXCLUDED.views,
                        likes = EXCLUDED.likes,
                        subscribers = EXCLUDED.subscribers,
                        recommended_videos = EXCLUDED.recommended_videos,
                        video_cloud_url = EXCLUDED.video_cloud_url,
                        music = EXCLUDED.music,
                        preview_image = EXCLUDED.preview_image,
                        transcript = EXCLUDED.transcript,
                        chapters = EXCLUDED.chapters
                """, (
                    # Basic Video Information
                    video_data.get('video_id'),
                    video_data.get('title'),
                    video_data.get('url'),
                    video_data.get('video_length'),
                    video_data.get('upload_date'),
                    video_data.get('date_posted'),
                    
                    # Channel Information
                    video_data.get('youtuber'),
                    video_data.get('handle_name'),
                    video_data.get('channel_url'),
                    video_data.get('channel_id'),
                    video_data.get('verified'),
                    
                    # Engagement Metrics
                    video_data.get('views'),
                    video_data.get('likes'),
                    video_data.get('dislikes'),
                    video_data.get('num_comments'),
                    video_data.get('subscribers'),
                    
                    # Content Details
                    (video_data.get('description', '') or '')[:1000],  # Increased limit
                    video_data.get('category'),
                    to_json(video_data.get('tags')),
                    to_json(video_data.get('hashtags')),
                    video_data.get('language'),
                    
                    # Technical Details
                    video_data.get('quality_label'),
                    video_data.get('fps'),
                    to_json(video_data.get('codecs')),
                    to_json(video_data.get('formats')),
                    to_json(video_data.get('thumbnails')),
                    to_json(video_data.get('captions')),
                    
                    # Transcript Data
                    to_json(video_data.get('formatted_transcript')),
                    video_data.get('transcript_text'),
                    
                    # Recommendations & Related
                    to_json(video_data.get('recommended_videos')),
                    to_json(video_data.get('next_recommended_videos')),
                    to_json(video_data.get('related_videos')),
                    
                    # Live Stream Data
                    video_data.get('is_live'),
                    video_data.get('was_live'),
                    video_data.get('live_start_time'),
                    video_data.get('live_end_time'),
                    video_data.get('concurrent_viewers'),
                    
                    # Age & Restrictions
                    video_data.get('age_limit'),
                    video_data.get('is_family_friendly'),
                    video_data.get('content_rating'),
                    
                    # Monetization
                    video_data.get('is_monetized'),
                    video_data.get('has_ads'),
                    
                    # Performance Metrics
                    video_data.get('view_count_24h'),
                    video_data.get('like_ratio'),
                    video_data.get('engagement_rate'),
                    
                    # Geographic Data
                    video_data.get('country'),
                    video_data.get('region'),
                    
                    # Video Analysis
                    video_data.get('duration_category'),
                    video_data.get('content_type'),
                    
                    # Enhanced BrightData Fields (automatically collected during discovery)
                    safe_extract('music'),
                    safe_extract('preview_image'),
                    safe_extract('shortcode'),
                    safe_extract('avatar_img_channel'),
                    safe_extract('is_sponsored'),
                    safe_extract('license'),
                    safe_extract('viewport_frames', force_json=True),
                    safe_extract('current_optimal_res'),
                    safe_extract('color'),
                    safe_extract('quality'),
                    safe_extract('post_type'),
                    safe_extract('youtuber_id'),
                    safe_extract('transcript', force_json=True),
                    safe_extract('transcript_language'),
                    safe_extract('chapters', force_json=True),
                    
                    # Discovery Agent Fields
                    video_data.get('num_recommendations', 0),
                    video_cloud_url,
                    True  # is_animated (since this is the animation discovery agent)
                ))
                conn.commit()
                
                action = "Updated" if is_update else "Inserted"
                
                # Count enhanced fields captured
                enhanced_fields = ['music', 'preview_image', 'shortcode', 'avatar_img_channel', 'is_sponsored',
                                 'license', 'viewport_frames', 'current_optimal_res', 'color', 'quality',
                                 'post_type', 'youtuber_id', 'transcript', 'transcript_language', 'chapters']
                enhanced_captured = len([f for f in enhanced_fields if video_data.get(f) is not None])
                
                logger.info(f"Comprehensive video {action.lower()} in database", extra={
                    "video_id": video_id,
                    "action": action,
                    "title": video_data.get('title'),
                    "table": "videos_full",
                    "has_cloud_url": bool(video_cloud_url),
                    "fields_captured": len([k for k, v in video_data.items() if v is not None]),
                    "enhanced_fields_captured": enhanced_captured
                })
                
        except Exception as e:
            logger.error(f"Failed to save comprehensive video to database: {str(e)}")
            logger.error(f"Video ID: {video_id}, Table: videos_full")
            raise