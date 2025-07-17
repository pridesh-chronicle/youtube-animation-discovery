#!/usr/bin/env python3

import os
import logging
import json
import threading
import time
import psutil
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
# Manual CORS preflight handler for maximum compatibility (especially Lovable/ngrok)
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', 
                           "Content-Type,Authorization,X-Requested-With,Accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers,ngrok-skip-browser-warning,User-Agent,Cache-Control,Pragma")
        response.headers.add('Access-Control-Allow-Methods', 
                           "GET,PUT,POST,DELETE,OPTIONS,PATCH")
        response.headers.add('Access-Control-Max-Age', '86400')
        return response

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 
                        "Content-Type,Authorization,X-Requested-With,Accept,Origin,Access-Control-Request-Method,Access-Control-Request-Headers,ngrok-skip-browser-warning,User-Agent,Cache-Control,Pragma")
    response.headers.add('Access-Control-Allow-Methods', 
                        "GET,PUT,POST,DELETE,OPTIONS,PATCH")
    return response

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
    discovery_stats.update({
        "total_animated": len(agent.animated_videos),
        "total_processed": len(agent.processed_videos),
        "queue_size": len(agent.queue),
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
        while agent.queue:  # Continue until queue is empty
            iteration += 1
            if not agent.queue:
                logger.info("Queue empty, stopping discovery")
                break
                
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

@app.route('/cors-test', methods=['GET', 'POST', 'OPTIONS'])
def cors_test():
    """CORS test endpoint specifically for Lovable integration"""
    return jsonify({
        "message": "CORS is working!",
        "method": request.method,
        "headers_received": dict(request.headers),
        "origin": request.headers.get('Origin', 'No origin header'),
        "user_agent": request.headers.get('User-Agent', 'No user agent'),
        "ngrok_header": request.headers.get('ngrok-skip-browser-warning', 'Not present'),
        "timestamp": datetime.now().isoformat()
    }), 200

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
        
        seed_videos = data.get('seed_videos', [
            'hwiyUuYZLHE', 'RtU8nBnpFVE', 'vffu6FG4YP4', '7LXaz9QIIBQ', 'oWlhMekUZRs',
            'e89ee8RgBAY', 'rMpQbSq9dJ8', '0X_zwGXv5e4', '-p1P4fdhaF8', 'ZfB9Krqs1jQ',
            'ha0SvMUpNRA', 'uNX0KjqmM8E', 'jGhf72_3dmw', '9ZFGeD9ApOs', '4HCFJ1klruE',
            'X3hq9NsjXos', 'dBVjXegJ468', 'MpgLfaarl7g', 'tbzGr-GNpaw', 'WpFrE1_ym7M',
            '0qbhZ-7S-9o', 'NV7eL9q7SZI', 'AJ59OqLO3Nk', 'kPOTBOoTYFE', 'bVpa7WRm3iY',
            'mWwDdIpnhlM', 'trfB_0ycTp0', 'CcgE0RNxWJw', 'ZKS033Q5LPs', 'oYRSagA4K6g',
            'n3OE2MdTZWc'
        ])
        save_videos = data.get('save_videos', False)   # Faster without video saving
        save_frames = data.get('save_frames', False)
        
        logger.info("Synchronous discovery started - will run until queue is empty")
        
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        animated_videos = agent.start_discovery(seed_videos)
        agent.save_results()
        
        return jsonify({
            "status": "completed",
            "results": {
                "animated_videos_found": len(animated_videos),
                "total_processed": len(agent.processed_videos),
                "queue_remaining": len(agent.queue),
                "completion_reason": "queue_empty" if not agent.queue else "processing_failed"
            }
        }), 200
        
    except Exception as e:
        logger.error("Synchronous discovery failed", extra={"error": str(e)})
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