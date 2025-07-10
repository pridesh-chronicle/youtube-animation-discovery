#!/usr/bin/env python3

from discovery_agent import DiscoveryAgent

def main():
    # Example seed videos (you can change these)
    seed_videos = [
        "hwiyUuYZLHE",  # Your example video
        "RtU8nBnpFVE"   # Your example video
    ]
    
    # Configuration flags for saving videos and frames
    save_videos = True   # Set to False to disable video saving
    save_frames = True   # Set to False to disable frame saving
    
    # Create and run discovery agent
    agent = DiscoveryAgent(save_videos=save_videos, save_frames=save_frames)
    
    print("🎬 YouTube Animation Discovery Agent")
    print("=" * 40)
    
    # Start discovery process
    animated_videos = agent.start_discovery(seed_videos, max_iterations=50)
    
    # Save results
    agent.save_results()
    
    print(f"\n🎉 Discovery complete!")
    print(f"Total animated videos found: {len(animated_videos)}")
    print(f"Total videos processed: {len(agent.processed_videos)}")
    print(f"📊 Data saved to SQLite database: {agent.db_filename}")
    print(f"💡 View with: sqlite3 {agent.db_filename}")
    print(f"💡 Or use DB Browser for SQLite: https://sqlitebrowser.org/")

if __name__ == "__main__":
    main() 