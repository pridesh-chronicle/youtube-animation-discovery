#!/usr/bin/env python3

import os
import logging
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, make_response
from discovery_agent import DiscoveryAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS is handled manually below to avoid duplicate headers
# Manual CORS handler for maximum compatibility (especially Lovable/ngrok)
@app.after_request
def after_request(response):
    # Always add CORS headers to all responses (including OPTIONS)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = "Content-Type,Authorization,X-Requested-With,Accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers,ngrok-skip-browser-warning,User-Agent,Cache-Control,Pragma"
    response.headers['Access-Control-Allow-Methods'] = "GET,PUT,POST,DELETE,OPTIONS,PATCH"
    response.headers['Access-Control-Max-Age'] = '86400'
    return response

# Handle OPTIONS preflight requests
@app.route('/<path:path>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def handle_options(path=None):
    """Handle preflight OPTIONS requests for any route"""
    return '', 200

# Global variables to track discovery state
discovery_stats = {
    "status": "idle",
    "start_time": None,
    "current_iteration": 0,
    "total_animated": 0,
    "total_processed": 0,
    "queue_size": 0,
    "last_update": None
}

discovery_thread = None

def update_discovery_stats(agent, iteration=None):
    """Update global discovery statistics"""
    global discovery_stats
    
    # Get cloud queue stats
    queue_stats = agent.queue.get_stats()
    
    discovery_stats.update({
        "total_animated": len(agent.animated_videos),
        "total_processed": len(agent.processed_videos),
        "queue_size": queue_stats.get('pending', 0),
        "queue_stats": queue_stats,
        "last_update": datetime.now().isoformat()
    })
    if iteration is not None:
        discovery_stats["current_iteration"] = iteration

def run_discovery_background(seed_videos, save_videos, save_frames):
    """Run discovery in background thread"""
    global discovery_stats
    
    try:
        discovery_stats["status"] = "running"
        discovery_stats["start_time"] = datetime.now().isoformat()
        discovery_stats["current_iteration"] = 0
        
        logger.info("Starting background discovery", extra={
            "seed_videos": seed_videos,
            "mode": "run_until_queue_empty"
        })
        
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        
        # Manual iteration loop for better progress tracking
        agent.add_to_queue(seed_videos)
        
        iteration = 0
        while True:  # Continue until queue is empty
            # Check if there are videos in the queue
            queue_stats = agent.queue.get_stats()
            if queue_stats.get('pending', 0) == 0:
                logger.info("Queue empty, stopping discovery")
                break
                
            iteration += 1
                
            logger.info(f"Background iteration {iteration}")
            
            if not agent.process_video_batch():
                logger.info("No videos processed, stopping discovery")
                break
                
            update_discovery_stats(agent, iteration)
        
        # Save results
        agent.save_results()
        
        discovery_stats["status"] = "completed"
        logger.info("Background discovery completed", extra={
            "total_iterations": iteration,
            "total_animated": len(agent.animated_videos),
            "total_processed": len(agent.processed_videos)
        })
        
    except Exception as e:
        discovery_stats["status"] = "error"
        discovery_stats["error"] = str(e)
        logger.error("Background discovery failed", extra={"error": str(e)})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "discovery_status": discovery_stats["status"],
        "cors_enabled": True
    }), 200


@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get comprehensive analytics and metrics"""
    try:
        from cloud_database import CloudDatabase
        db = CloudDatabase()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Basic database metrics (animated videos only)
            cursor.execute("SELECT COUNT(*) FROM videos_full WHERE is_animated = true")
            total_videos = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT youtuber) FROM videos_full WHERE youtuber IS NOT NULL AND youtuber != '' AND is_animated = true")
            total_creators = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(views) FROM videos_full WHERE views IS NOT NULL AND is_animated = true")
            total_views_result = cursor.fetchone()[0]
            total_views = int(total_views_result) if total_views_result else 0
            
            # 1. Last 5 videos added to the database
            cursor.execute("""
                SELECT video_id, title, youtuber, views, discovered_at, url
                FROM videos_full 
                WHERE is_animated = true
                ORDER BY discovered_at DESC 
                LIMIT 5
            """)
            recent_videos = []
            for row in cursor.fetchall():
                recent_videos.append({
                    "video_id": row[0],
                    "title": row[1],
                    "creator": row[2],
                    "views": int(row[3]) if row[3] else 0,
                    "discovered_at": row[4].isoformat() if row[4] else None,
                    "url": row[5]
                })
            
            # 2. Top creators by different metrics
            # Top creators by view count
            cursor.execute("""
                SELECT youtuber, SUM(views) as total_views, COUNT(*) as video_count, AVG(subscribers) as avg_subscribers
                FROM videos_full 
                WHERE youtuber IS NOT NULL AND youtuber != '' AND views IS NOT NULL
                AND is_animated = true
                GROUP BY youtuber 
                ORDER BY total_views DESC 
                LIMIT 5
            """)
            top_creators_by_views = []
            for row in cursor.fetchall():
                top_creators_by_views.append({
                    "creator": row[0],
                    "total_views": int(row[1]) if row[1] else 0,
                    "video_count": row[2],
                    "avg_subscribers": int(row[3]) if row[3] else 0
                })
            
            # Top creators by subscriber count
            cursor.execute("""
                SELECT youtuber, MAX(subscribers) as max_subscribers, SUM(views) as total_views, COUNT(*) as video_count
                FROM videos_full 
                WHERE youtuber IS NOT NULL AND youtuber != '' AND subscribers IS NOT NULL
                AND is_animated = true
                GROUP BY youtuber 
                ORDER BY max_subscribers DESC 
                LIMIT 5
            """)
            top_creators_by_subscribers = []
            for row in cursor.fetchall():
                top_creators_by_subscribers.append({
                    "creator": row[0],
                    "subscribers": int(row[1]) if row[1] else 0,
                    "total_views": int(row[2]) if row[2] else 0,
                    "video_count": row[3]
                })
            
            # Top creators by engagement rate
            cursor.execute("""
                SELECT youtuber, 
                       SUM(views) as total_views,
                       SUM(likes) as total_likes,
                       SUM(num_comments) as total_comments,
                       MAX(subscribers) as max_subscribers,
                       COUNT(*) as video_count,
                       CASE 
                           WHEN SUM(views) > 0 THEN 
                               ((SUM(COALESCE(likes, 0)) + SUM(COALESCE(num_comments, 0)) + MAX(COALESCE(subscribers, 0))) * 100.0 / SUM(views))
                           ELSE 0 
                       END as engagement_rate
                FROM videos_full 
                WHERE youtuber IS NOT NULL AND youtuber != '' AND views IS NOT NULL AND views > 0
                AND is_animated = true
                GROUP BY youtuber 
                ORDER BY engagement_rate DESC 
                LIMIT 5
            """)
            top_creators_by_engagement = []
            for row in cursor.fetchall():
                top_creators_by_engagement.append({
                    "creator": row[0],
                    "total_views": int(row[1]) if row[1] else 0,
                    "total_likes": int(row[2]) if row[2] else 0,
                    "total_comments": int(row[3]) if row[3] else 0,
                    "subscribers": int(row[4]) if row[4] else 0,
                    "video_count": row[5],
                    "engagement_rate": round(float(row[6]), 2) if row[6] else 0
                })
            
            # 3. Top videos by date ranges
            date_ranges = {
                "1d": "1 day",
                "7d": "7 days", 
                "1m": "1 month",
                "1y": "1 year"
            }
            
            top_videos_by_period = {}
            
            for period, interval in date_ranges.items():
                cursor.execute(f"""
                    SELECT video_id, title, youtuber, views, date_posted, url
                    FROM videos_full 
                    WHERE date_posted >= CURRENT_DATE - INTERVAL '{interval}'
                    AND views IS NOT NULL
                    AND is_animated = true
                    ORDER BY views DESC 
                    LIMIT 5
                """)
                
                period_videos = []
                for row in cursor.fetchall():
                    period_videos.append({
                        "video_id": row[0],
                        "title": row[1],
                        "creator": row[2],
                        "views": int(row[3]) if row[3] else 0,
                        "date_posted": row[4].isoformat() if row[4] else None,
                        "url": row[5]
                    })
                top_videos_by_period[period] = period_videos
            
            # All time top videos
            cursor.execute("""
                SELECT video_id, title, youtuber, views, date_posted, url
                FROM videos_full 
                WHERE views IS NOT NULL
                AND is_animated = true
                ORDER BY views DESC 
                LIMIT 5
            """)
            all_time_top_videos = []
            for row in cursor.fetchall():
                all_time_top_videos.append({
                    "video_id": row[0],
                    "title": row[1],
                    "creator": row[2],
                    "views": int(row[3]) if row[3] else 0,
                    "date_posted": row[4].isoformat() if row[4] else None,
                    "url": row[5]
                })
            top_videos_by_period["all_time"] = all_time_top_videos
            
            # 4. Up and coming videos (posted <30 days, ordered by views/day)
            cursor.execute("""
                SELECT video_id, title, youtuber, views, date_posted, url,
                       CASE 
                           WHEN date_posted IS NOT NULL THEN 
                               views::float / GREATEST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - date_posted))::float / 86400, 1)
                           ELSE 0 
                       END as views_per_day
                FROM videos_full 
                WHERE date_posted >= CURRENT_TIMESTAMP - INTERVAL '30 days'
                AND views IS NOT NULL AND views > 0
                AND is_animated = true
                ORDER BY views_per_day DESC 
                LIMIT 5
            """)
            up_and_coming_videos = []
            for row in cursor.fetchall():
                up_and_coming_videos.append({
                    "video_id": row[0],
                    "title": row[1],
                    "creator": row[2],
                    "views": int(row[3]) if row[3] else 0,
                    "date_posted": row[4].isoformat() if row[4] else None,
                    "url": row[5],
                    "views_per_day": round(float(row[6]), 2) if row[6] else 0
                })
            
            # 5. Up and coming creators (<50k subs, ordered by velocity)
            cursor.execute("""
                WITH creator_metrics AS (
                    SELECT youtuber,
                           MAX(subscribers) as max_subscribers,
                           SUM(views) as total_views,
                           COUNT(*) as video_count,
                           MIN(date_posted) as first_posted,
                           MAX(date_posted) as latest_posted
                    FROM videos_full 
                    WHERE youtuber IS NOT NULL AND youtuber != '' 
                    AND subscribers IS NOT NULL AND subscribers < 50000
                    AND date_posted IS NOT NULL
                    AND is_animated = true
                    GROUP BY youtuber
                )
                SELECT youtuber, max_subscribers, total_views, video_count, first_posted, latest_posted,
                       CASE 
                           WHEN first_posted IS NOT NULL THEN 
                               total_views::float / GREATEST(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - first_posted))::float / 86400, 1)
                           ELSE 0 
                       END as velocity
                FROM creator_metrics
                WHERE first_posted IS NOT NULL
                ORDER BY velocity DESC 
                LIMIT 5
            """)
            up_and_coming_creators = []
            for row in cursor.fetchall():
                up_and_coming_creators.append({
                    "creator": row[0],
                    "subscribers": int(row[1]) if row[1] else 0,
                    "total_views": int(row[2]) if row[2] else 0,
                    "video_count": row[3],
                    "first_posted": row[4].isoformat() if row[4] else None,
                    "latest_posted": row[5].isoformat() if row[5] else None,
                    "velocity": round(float(row[6]), 2) if row[6] else 0
                })
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "database_overview": {
                "total_videos": total_videos,
                "total_creators": total_creators,
                "total_views": total_views
            },
            "recent_videos": recent_videos,
            "top_creators": {
                "by_views": top_creators_by_views,
                "by_subscribers": top_creators_by_subscribers,
                "by_engagement": top_creators_by_engagement
            },
            "top_videos": top_videos_by_period,
            "up_and_coming": {
                "videos": up_and_coming_videos,
                "creators": up_and_coming_creators
            },
            "discovery_agent_status": discovery_stats["status"],
            "current_queue_size": discovery_stats.get("queue_size", 0)
        }), 200
        
    except Exception as e:
        logger.error("Failed to get comprehensive metrics", extra={"error": str(e)})
        return jsonify({
            "error": "Failed to retrieve metrics",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get current discovery status"""
    return jsonify(discovery_stats), 200

@app.route('/discover', methods=['POST'])
def start_discovery():
    """Start discovery process via HTTP endpoint"""
    global discovery_thread
    
    # Check if discovery is already running
    if discovery_stats["status"] == "running":
        return jsonify({
            "error": "Discovery already running",
            "current_stats": discovery_stats
        }), 409
    
    try:
        data = request.get_json() or {}
        
        # Configuration with defaults
        seed_videos = data.get('seed_videos', [
            'hwiyUuYZLHE', 'RtU8nBnpFVE', 'vffu6FG4YP4', '7LXaz9QIIBQ', 'oWlhMekUZRs',
            'e89ee8RgBAY', 'rMpQbSq9dJ8', '0X_zwGXv5e4', '-p1P4fdhaF8', 'ZfB9Krqs1jQ',
            'ha0SvMUpNRA', 'uNX0KjqmM8E', 'jGhf72_3dmw', '9ZFGeD9ApOs', '4HCFJ1klruE',
            'X3hq9NsjXos', 'dBVjXegJ468', 'MpgLfaarl7g', 'tbzGr-GNpaw', 'WpFrE1_ym7M',
            '0qbhZ-7S-9o', 'NV7eL9q7SZI', 'AJ59OqLO3Nk', 'kPOTBOoTYFE', 'bVpa7WRm3iY',
            'mWwDdIpnhlM', 'trfB_0ycTp0', 'CcgE0RNxWJw', 'ZKS033Q5LPs', 'oYRSagA4K6g',
            'n3OE2MdTZWc'
        ])
        save_videos = data.get('save_videos', True)
        save_frames = data.get('save_frames', False)
        
        logger.info("Discovery requested via API", extra={
            "seed_videos": seed_videos,
            "save_videos": save_videos,
            "save_frames": save_frames,
            "mode": "run_until_queue_empty"
        })
        
        # Start discovery in background thread
        discovery_thread = threading.Thread(
            target=run_discovery_background,
            args=(seed_videos, save_videos, save_frames)
        )
        discovery_thread.daemon = True
        discovery_thread.start()
        
        return jsonify({
            "message": "Discovery started - will run until queue is empty",
            "config": {
                "seed_videos": seed_videos,
                "save_videos": save_videos,
                "save_frames": save_frames,
                "mode": "run_until_queue_empty"
            },
            "status_url": "/status"
        }), 202
        
    except Exception as e:
        logger.error("Failed to start discovery", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500

@app.route('/discover/sync', methods=['POST'])
def start_discovery_sync():
    """Start discovery process synchronously (blocks until complete)"""
    try:
        data = request.get_json() or {}
        seed_videos = data.get('seed_videos', ['hwiyUuYZLHE'])
        save_videos = data.get('save_videos', True)
        save_frames = data.get('save_frames', False)
        
        logger.info("Sync discovery requested", extra={
            "seed_videos": seed_videos,
            "save_videos": save_videos,
            "save_frames": save_frames
        })
        
        # Create and run agent directly (synchronous)
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        
        # Add seed videos and run discovery
        agent.add_to_queue(seed_videos)
        results = agent.run_discovery()
        
        # Get final stats
        queue_stats = agent.queue.get_stats()
        
        return jsonify({
            "message": "Discovery completed",
            "results": {
                "total_animated": len(agent.animated_videos),
                "total_processed": len(agent.processed_videos),
                "animated_videos": [video.to_dict() for video in agent.animated_videos[:10]],  # First 10
                "queue_stats": queue_stats
            }
        }), 200
        
    except Exception as e:
        logger.error("Sync discovery failed", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    """Get recent log entries"""
    try:
        count = int(request.args.get('count', 50))
        
        try:
            with open('discovery_agent.log', 'r') as f:
                lines = f.readlines()[-count:]
            
            return jsonify({
                "logs": [line.strip() for line in lines],
                "count": len(lines)
            }), 200
            
        except FileNotFoundError:
            return jsonify({
                "logs": [],
                "message": "No log file found"
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """API documentation"""
    return jsonify({
        "service": "YouTube Animation Discovery Agent",
        "version": "1.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "GET /status": "Get discovery status",
            "POST /discover": "Start async discovery",
            "POST /discover/sync": "Start sync discovery",
            "GET /logs?count=N": "Get recent logs"
        },
        "example_request": {
            "url": "/discover",
            "method": "POST",
            "body": {
                "seed_videos": ["hwiyUuYZLHE", "RtU8nBnpFVE"],
                "max_iterations": 10,
                "save_videos": True,
                "save_frames": False
            }
        }
    }), 200

@app.route('/queue/stats', methods=['GET'])
def get_queue_stats():
    """Get comprehensive queue statistics"""
    try:
        from cloud_database import CloudDatabase
        from discovery_queue import DiscoveryQueue
        
        db = CloudDatabase()
        queue = DiscoveryQueue(db.get_connection)
        
        stats = queue.get_stats()
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "queue_stats": stats,
            "discovery_agent_status": discovery_stats["status"]
        }), 200
        
    except Exception as e:
        logger.error("Failed to get queue stats", extra={"error": str(e)})
        return jsonify({
            "error": "Failed to retrieve queue stats",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/queue/add', methods=['POST'])
def add_to_queue_endpoint():
    """Add videos to the discovery queue"""
    try:
        data = request.get_json() or {}
        video_ids = data.get('video_ids', [])
        priority = data.get('priority', 0)
        source_video_id = data.get('source_video_id')
        
        if not video_ids:
            return jsonify({
                "error": "No video_ids provided",
                "timestamp": datetime.now().isoformat()
            }), 400
        
        from cloud_database import CloudDatabase
        from discovery_queue import DiscoveryQueue
        
        db = CloudDatabase()
        queue = DiscoveryQueue(db.get_connection)
        
        added_count = queue.add_videos(video_ids, source_video_id)
        
        return jsonify({
            "message": f"Added {added_count} videos to queue",
            "added_count": added_count,
            "total_requested": len(video_ids),
            "duplicates_skipped": len(video_ids) - added_count,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error("Failed to add videos to queue", extra={"error": str(e)})
        return jsonify({
            "error": "Failed to add videos to queue",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/queue/cleanup', methods=['POST'])
def cleanup_queue():
    """Clean up old queue entries"""
    try:
        data = request.get_json() or {}
        days_old = data.get('days_old', 7)
        
        from cloud_database import CloudDatabase
        from discovery_queue import DiscoveryQueue
        
        db = CloudDatabase()
        queue = DiscoveryQueue(db.get_connection)
        
        # Clean up old entries
        deleted_count = queue.cleanup_old_completed(days_old)
        
        # Reset stuck processing videos
        reset_count = queue.reset_stuck_processing()
        
        return jsonify({
            "message": "Queue cleanup completed",
            "deleted_old_entries": deleted_count,
            "reset_stuck_processing": reset_count,
            "days_old_threshold": days_old,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error("Failed to cleanup queue", extra={"error": str(e)})
        return jsonify({
            "error": "Failed to cleanup queue",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def main():
    """Main function for local testing"""
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting YouTube Discovery Agent on port {port}")
    
    if 'PORT' in os.environ:
        # Running in Cloud Run
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Local development
        logger.info("Running in local development mode")
        app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main() 