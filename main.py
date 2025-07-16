#!/usr/bin/env python3

import logging
from discovery_agent import DiscoveryAgent

# Configure logging for main
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Example seed videos (you can change these)
    seed_videos = [
        "hwiyUuYZLHE",  # Your example video
        "RtU8nBnpFVE",  # Your example video
        "Bl1FOKpFY2Q"   # Your example video
    ]
    
    # Configuration flags for saving videos and frames
    save_videos = True   # Set to False to disable video saving
    save_frames = True   # Set to False to disable frame saving
    
    logger.info("🎬 YouTube Animation Discovery Agent Starting")
    logger.info("=" * 50)
    
    try:
        # Create and run discovery agent
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        
        # Start discovery process
        animated_videos = agent.start_discovery(seed_videos, max_iterations=1000)
        
        # Save results
        agent.save_results()
        
        # Final summary
        logger.info("🎉 Discovery complete!")
        logger.info(f"📊 Results Summary:")
        logger.info(f"   • Total animated videos found: {len(animated_videos)}")
        logger.info(f"   • Total videos processed: {len(agent.processed_videos)}")
        logger.info(f"   • Videos remaining in queue: {len(agent.queue)}")
        logger.info(f"   • Database: animated_videos.db")
        logger.info(f"   • Log file: discovery_agent.log")
        
    except Exception as e:
        logger.error(f"Discovery failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 