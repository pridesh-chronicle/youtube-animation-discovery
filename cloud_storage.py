import os
from google.cloud import storage

class CloudStorage:
    def __init__(self):
        try:
            self.client = storage.Client()
            self.bucket_name = os.getenv("STORAGE_BUCKET_NAME")
            self.bucket = self.client.bucket(self.bucket_name) if self.bucket_name else None
            print(f"✅ Cloud Storage initialized: {self.bucket_name}")
        except Exception as e:
            print(f"❌ Cloud Storage failed: {e}")
            self.bucket = None
    
    def upload_video(self, local_path, video_id):
        """Upload video to Cloud Storage"""
        if not self.bucket:
            return None
        try:
            blob_name = f"videos/{video_id}.mp4"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            print(f"✅ Video uploaded: gs://{self.bucket_name}/{blob_name}")
            return f"gs://{self.bucket_name}/{blob_name}"
        except Exception as e:
            print(f"❌ Video upload failed: {e}")
            return None
    
    def test_upload(self):
        """Test upload with a simple text file"""
        if not self.bucket:
            return False
        try:
            with open("test.txt", "w") as f:
                f.write("Hello Cloud Storage!")
            
            blob = self.bucket.blob("test/test.txt")
            blob.upload_from_filename("test.txt")
            os.remove("test.txt")
            
            print(f"✅ Test upload successful: gs://{self.bucket_name}/test/test.txt")
            return True
        except Exception as e:
            print(f"❌ Test upload failed: {e}")
            return False