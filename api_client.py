import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

class BrightDataClient:
    def __init__(self):
        self.api_key = os.getenv("BRIGHT_DATA_API_KEY")
        self.api_url = os.getenv("BRIGHT_DATA_API_URL")
        self.dataset_id = os.getenv("BRIGHT_DATA_DATASET_ID")
        self.base_url = "https://api.brightdata.com/datasets/v3"
    
    def fetch_videos(self, video_urls):
        """Fetch video data from Bright Data API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = [{"url": url, "country": "", "transcription_language": ""} for url in video_urls]
        url = f"{self.api_url}?dataset_id={self.dataset_id}&include_errors=true"
        
        # Step 1: Submit request and get snapshot_id
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        
        if 'snapshot_id' not in result:
            print(f"Error: No snapshot_id in response: {result}")
            return []
        
        snapshot_id = result['snapshot_id']
        print(f"Got snapshot_id: {snapshot_id}")
        
        # Step 2: Wait for data to be ready and fetch it
        return self.wait_for_snapshot(snapshot_id)
    
    def wait_for_snapshot(self, snapshot_id, max_wait_time=300):
        """Wait for snapshot to be ready and fetch the data"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/snapshot/{snapshot_id}?format=json"
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            response = requests.get(url, headers=headers)
            
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Response status: {response.status_code}")
                print(f"Response text: {response.text[:500]}...")
                return []
            
            # Check if data is a list (direct video data)
            if isinstance(data, list):
                print("Data received directly as list")
                return data
            
            # Check if it's a status response
            if isinstance(data, dict) and 'status' in data:
                print(f"Snapshot status: {data['status']}")
                
                if data['status'] == 'ready':
                    print("Data is ready, fetching...")
                    return self.fetch_snapshot_data(snapshot_id)
                elif data['status'] == 'failed':
                    print(f"Snapshot failed: {data}")
                    return []
                else:
                    print("Waiting for data to be ready...")
                    time.sleep(10)
            else:
                print(f"Unexpected response format: {type(data)}")
                print(f"Data: {data}")
                return []
        
        print("Timeout waiting for snapshot to be ready")
        return []
    
    def fetch_snapshot_data(self, snapshot_id):
        """Fetch the actual data from a ready snapshot"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/snapshot/{snapshot_id}?format=json"
        
        response = requests.get(url, headers=headers)
        
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as e:
            print(f"JSON decode error in fetch_snapshot_data: {e}")
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text[:500]}...")
            return []
    
    def get_recommendations(self, video_data):
        """Extract recommendation video IDs from video data"""
        recommendations = []
        
        # Extract from recommended_videos (array of URLs)
        if video_data.get("recommended_videos"):
            for video in video_data["recommended_videos"]:
                if "watch?v=" in video['url']:
                    video_id = video['url'].split("watch?v=")[1].split("&")[0]
                    recommendations.append(video_id)
        
        # Extract from next_recommended_videos (array of URLs)
        if video_data.get("next_recommended_videos"):
            for video in video_data["next_recommended_videos"]:
                if "watch?v=" in video['url']:
                    video_id = video['url'].split("watch?v=")[1].split("&")[0]
                    recommendations.append(video_id)
        
        # Extract from related_videos (array of URLs)
        if video_data.get("related_videos"):
            for video in video_data["related_videos"]:
                if "watch?v=" in video['url']:
                    video_id = video['url'].split("watch?v=")[1].split("&")[0]
                    recommendations.append(video_id)
        
        return list(set(recommendations))  # Remove duplicates 