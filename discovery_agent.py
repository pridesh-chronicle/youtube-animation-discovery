import json
import time
import sqlite3
from api_client import BrightDataClient
from animation_detector import is_animated

class DiscoveryAgent:
    def __init__(self):
        self.client = BrightDataClient()
        self.processed_videos = set()  # Global set to track processed videos
        self.animated_videos = []      # Store animated videos found
        self.queue = []               # Queue of videos to process
        self.db_filename = "animated_videos.db"
        self.setup_database()
        
    def add_to_queue(self, video_ids):
        """Add video IDs to queue if not already processed"""
        for video_id in video_ids:
            if video_id not in self.processed_videos and video_id not in self.queue:
                self.queue.append(video_id)
                print(f"Added to queue: {video_id}")
    
    def process_video_batch(self, batch_size=10):
        """Process a batch of videos from the queue"""
        if not self.queue:
            return False
        
        # Get batch from queue
        batch = self.queue[:batch_size]
        self.queue = self.queue[batch_size:]
        
        # Convert to URLs and fetch data
        video_urls = [f"https://www.youtube.com/watch?v={video_id}" for video_id in batch]
        video_data_list = self.client.fetch_videos(video_urls)
        
        if not video_data_list:
            print("No video data returned from API")
            return False
        
        for video_data in video_data_list:
            video_id = video_data.get('video_id')
            video_url = video_data.get('url')
            
            # Mark as processed
            self.processed_videos.add(video_id)
            
            # Check if animated
            if is_animated(video_url):
                print(f"✅ Found animated video: {video_data.get('title', 'Unknown')}")
                self.animated_videos.append(video_data)
                
                # Save to SQLite database immediately
                self.save_to_sqlite(video_data)
                print(f"📊 Saved to database: {len(self.animated_videos)} total videos")
                
                # Get recommendations and add to queue
                recommendations = self.client.get_recommendations(video_data)
                self.add_to_queue(recommendations)
            else:
                print(f"❌ Not animated: {video_data.get('title', 'Unknown')}")
        
        return True
    
    def start_discovery(self, seed_video_ids, max_iterations=100):
        """Start the discovery process"""
        print(f"🚀 Starting discovery with {len(seed_video_ids)} seed videos")
        
        # Add seed videos to queue
        self.add_to_queue(seed_video_ids)
        
        # Process videos
        for i in range(max_iterations):
            print(f"\n--- Iteration {i+1} ---")
            print(f"Queue size: {len(self.queue)}")
            print(f"Processed: {len(self.processed_videos)}")
            print(f"Animated found: {len(self.animated_videos)}")
            
            if not self.process_video_batch():
                print("Queue empty, stopping discovery")
                break
            
            # Small delay to be respectful to APIs
            time.sleep(1)
        
        return self.animated_videos
    
    def setup_database(self):
        """Create SQLite database and table"""
        conn = sqlite3.connect(self.db_filename)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                views INTEGER,
                likes INTEGER,
                num_comments INTEGER,
                subscribers INTEGER,
                video_length INTEGER,
                date_posted TEXT,
                youtuber TEXT,
                handle_name TEXT,
                channel_url TEXT,
                description TEXT,
                quality_label TEXT,
                verified BOOLEAN,
                num_recommendations INTEGER,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"📊 Database initialized: {self.db_filename}")
    
    def save_to_sqlite(self, video_data):
        """Save a single video to SQLite database"""
        conn = sqlite3.connect(self.db_filename)
        cursor = conn.cursor()
        
        # Count total recommendations
        recommendations = self.client.get_recommendations(video_data)
        
        cursor.execute('''
            INSERT OR REPLACE INTO videos (
                video_id, title, url, views, likes, num_comments, subscribers,
                video_length, date_posted, youtuber, handle_name, channel_url,
                description, quality_label, verified, num_recommendations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
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
            video_data.get('description', '')[:500],  # Limit description length
            video_data.get('quality_label'),
            video_data.get('verified'),
            len(recommendations)
        ))
        
        conn.commit()
        conn.close()
    
    def save_results(self, filename="animated_videos.json"):
        """Save discovered animated videos to file"""
        with open(filename, 'w') as f:
            json.dump(self.animated_videos, f, indent=2)
        print(f"💾 Saved {len(self.animated_videos)} animated videos to {filename}") 