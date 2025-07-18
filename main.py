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
    # Extended seed videos from user's comprehensive list
    seed_videos = [
        'hwiyUuYZLHE', 'RtU8nBnpFVE', 'vffu6FG4YP4', '7LXaz9QIIBQ', 'oWlhMekUZRs',
        'e89ee8RgBAY', 'rMpQbSq9dJ8', '0X_zwGXv5e4', '-p1P4fdhaF8', 'ZfB9Krqs1jQ',
        'ha0SvMUpNRA', 'uNX0KjqmM8E', 'jGhf72_3dmw', '9ZFGeD9ApOs', '4HCFJ1klruE',
        'X3hq9NsjXos', 'dBVjXegJ468', 'MpgLfaarl7g', 'tbzGr-GNpaw', 'WpFrE1_ym7M',
        '0qbhZ-7S-9o', 'NV7eL9q7SZI', 'AJ59OqLO3Nk', 'kPOTBOoTYFE', 'bVpa7WRm3iY',
        'mWwDdIpnhlM', 'trfB_0ycTp0', 'CcgE0RNxWJw', 'ZKS033Q5LPs', 'oYRSagA4K6g',
        'n3OE2MdTZWc'
    ]
    
    # Configuration flags for saving videos and frames
    save_videos = True   # Set to False to disable video saving
    save_frames = True   # Set to False to disable frame saving
    
    logger.info("🎬 YouTube Animation Discovery Agent Starting")
    logger.info("=" * 50)
    
    try:
        # Create and run discovery agent
        agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
        
        # Start discovery process - runs until queue is empty
        logger.info("🔄 Running discovery until queue is empty...")
        animated_videos = agent.start_discovery(seed_videos)
        
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