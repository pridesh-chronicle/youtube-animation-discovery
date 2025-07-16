#!/usr/bin/env python3

import os
import logging
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from discovery_agent import DiscoveryAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

def run_discovery_background(seed_videos, max_iterations, save_videos, save_frames):
    """Run discovery in background thread"""
    global discovery_stats
    
    try:
        discovery_stats["status"] = "running"
        discovery_stats["start_time"] = datetime.now().isoformat()
        discovery_stats["current_iteration"] = 0
        
        logger.info("Starting background discovery", extra={
            "seed_videos": seed_videos,
            "max_iterations": max_iterations
        })
        
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        
        # Manual iteration loop for better progress tracking
        agent.add_to_queue(seed_videos)
        
        for i in range(max_iterations):
            if not agent.queue:
                logger.info("Queue empty, stopping discovery")
                break
                
            logger.info(f"Background iteration {i+1}/{max_iterations}")
            
            if not agent.process_video_batch():
                break
                
            update_discovery_stats(agent, i+1)
        
        # Save results
        agent.save_results()
        
        discovery_stats["status"] = "completed"
        logger.info("Background discovery completed", extra={
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
        "discovery_status": discovery_stats["status"]
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
            "hwiyUuYZLHE",
            "RtU8nBnpFVE", 
            "Bl1FOKpFY2Q"
        ])
        max_iterations = data.get('max_iterations', 10)
        save_videos = data.get('save_videos', True)
        save_frames = data.get('save_frames', False)
        
        logger.info("Discovery requested via API", extra={
            "seed_videos": seed_videos,
            "max_iterations": max_iterations,
            "save_videos": save_videos,
            "save_frames": save_frames
        })
        
        # Start discovery in background thread
        discovery_thread = threading.Thread(
            target=run_discovery_background,
            args=(seed_videos, max_iterations, save_videos, save_frames)
        )
        discovery_thread.daemon = True
        discovery_thread.start()
        
        return jsonify({
            "message": "Discovery started",
            "config": {
                "seed_videos": seed_videos,
                "max_iterations": max_iterations,
                "save_videos": save_videos,
                "save_frames": save_frames
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
        
        seed_videos = data.get('seed_videos', ["hwiyUuYZLHE", "RtU8nBnpFVE"])
        max_iterations = data.get('max_iterations', 5)  # Smaller default for sync
        save_videos = data.get('save_videos', False)   # Faster without video saving
        save_frames = data.get('save_frames', False)
        
        logger.info("Synchronous discovery started")
        
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        animated_videos = agent.start_discovery(seed_videos, max_iterations)
        agent.save_results()
        
        return jsonify({
            "status": "completed",
            "results": {
                "animated_videos_found": len(animated_videos),
                "total_processed": len(agent.processed_videos),
                "queue_remaining": len(agent.queue)
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