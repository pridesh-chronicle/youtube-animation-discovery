import os
import requests
import time
import logging
import json
from dotenv import load_dotenv

load_dotenv()

# Custom exceptions for better error handling
class BrightDataTimeoutError(Exception):
    """Raised when BrightData API times out"""
    pass

class BrightDataAPIError(Exception): 
    """Raised when BrightData API returns an error"""
    pass

# Configure logging for API client
logger = logging.getLogger(__name__)

class BrightDataClient:
    def __init__(self):
        self.api_key = os.getenv("BRIGHT_DATA_API_KEY")
        self.api_url = os.getenv("BRIGHT_DATA_API_URL")
        self.dataset_id = os.getenv("BRIGHT_DATA_DATASET_ID")
        self.base_url = "https://api.brightdata.com/datasets/v3"
        
        logger.info("BrightData API client initialized", extra={
            "api_url": self.api_url,
            "dataset_id": self.dataset_id,
            "has_api_key": bool(self.api_key)
        })
    
    def _mask_sensitive_data(self, headers):
        """Mask sensitive data in headers for logging"""
        masked_headers = headers.copy()
        if 'Authorization' in masked_headers:
            masked_headers['Authorization'] = f"Bearer {'*' * 20}...{self.api_key[-4:] if self.api_key else 'None'}"
        return masked_headers
    
    def _log_request(self, method, url, headers=None, payload=None):
        """Log HTTP request details"""
        logger.info(f"🌐 BrightData API Request: {method} {url}", extra={
            "method": method,
            "url": url,
            "headers": self._mask_sensitive_data(headers) if headers else None,
            "payload_size": len(json.dumps(payload)) if payload else 0,
            "payload_items": len(payload) if isinstance(payload, list) else None
        })
        
        if payload and logger.isEnabledFor(logging.DEBUG):
            logger.debug("Request payload", extra={
                "payload": payload if len(json.dumps(payload)) < 1000 else f"{str(payload)[:500]}...(truncated)"
            })
    
    def _log_response(self, response, request_start_time):
        """Log HTTP response details"""
        duration = time.time() - request_start_time
        
        try:
            response_data = response.json() if response.content else {}
            response_size = len(response.content)
            
            logger.info(f"📡 BrightData API Response: {response.status_code}", extra={
                "status_code": response.status_code,
                "duration_seconds": round(duration, 3),
                "response_size_bytes": response_size,
                "content_type": response.headers.get('content-type', 'unknown'),
                "has_snapshot_id": 'snapshot_id' in response_data if isinstance(response_data, dict) else False,
                "response_type": type(response_data).__name__,
                "response_length": len(response_data) if isinstance(response_data, list) else None
            })
            
            # Log response headers (useful for debugging)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Response headers", extra={
                    "headers": dict(response.headers)
                })
            
            # Log response data (with truncation for large responses)
            if logger.isEnabledFor(logging.DEBUG):
                if response_size > 5000:  # Large response
                    logger.debug("Response data (truncated)", extra={
                        "response_preview": str(response_data)[:1000] + "...(truncated)"
                    })
                else:
                    logger.debug("Response data", extra={
                        "response_data": response_data
                    })
            
        except Exception as e:
            logger.warning("Could not parse response as JSON", extra={
                "error": str(e),
                "status_code": response.status_code,
                "duration_seconds": round(duration, 3),
                "response_text_preview": response.text[:500] if response.text else "No content"
            })
    
    def fetch_videos(self, video_urls):
        """Fetch video data from Bright Data API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = [{"url": url, "country": "", "transcription_language": ""} for url in video_urls]
        url = f"{self.api_url}?dataset_id={self.dataset_id}&include_errors=true"
        
        logger.info("Starting BrightData video fetch", extra={
            "video_count": len(video_urls),
            "video_urls": video_urls
        })
        
        # Step 1: Submit request and get snapshot_id
        self._log_request("POST", url, headers, payload)
        request_start_time = time.time()
        
        response = requests.post(url, headers=headers, json=payload)
        self._log_response(response, request_start_time)
        
        try:
            result = response.json()
        except requests.exceptions.JSONDecodeError as e:
            logger.error("Failed to parse initial request response as JSON", extra={
                "error": str(e),
                "status_code": response.status_code,
                "response_text": response.text[:500]
            })
            raise BrightDataAPIError(f"JSON decode error: {str(e)}")
        
        if 'snapshot_id' not in result:
            logger.error("No snapshot_id in response", extra={
                "response": result,
                "status_code": response.status_code
            })
            raise BrightDataAPIError(f"No snapshot_id in response: {result}")
        
        snapshot_id = result['snapshot_id']
        logger.info("Received snapshot_id, waiting for data", extra={
            "snapshot_id": snapshot_id
        })
        
        # Step 2: Wait for data to be ready and fetch it
        return self.wait_for_snapshot(snapshot_id)
    
    def wait_for_snapshot(self, snapshot_id, max_wait_time=300):
        """Wait for snapshot to be ready and fetch the data"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/snapshot/{snapshot_id}?format=json"
        
        logger.info("Starting snapshot polling", extra={
            "snapshot_id": snapshot_id,
            "max_wait_time": max_wait_time,
            "polling_url": url
        })
        
        start_time = time.time()
        poll_count = 0
        
        while time.time() - start_time < max_wait_time:
            poll_count += 1
            elapsed_time = time.time() - start_time
            
            logger.debug(f"Polling snapshot (attempt {poll_count})", extra={
                "snapshot_id": snapshot_id,
                "poll_count": poll_count,
                "elapsed_seconds": round(elapsed_time, 1)
            })
            
            self._log_request("GET", url, headers)
            request_start_time = time.time()
            
            response = requests.get(url, headers=headers)
            self._log_response(response, request_start_time)
            
            try:
                data = response.json()
            except requests.exceptions.JSONDecodeError as e:
                logger.error("JSON decode error during polling", extra={
                    "error": str(e),
                    "status_code": response.status_code,
                    "response_text": response.text[:500],
                    "snapshot_id": snapshot_id,
                    "poll_count": poll_count
                })
                # For polling errors, wait a bit and continue rather than failing completely
                time.sleep(10)
                continue
            
            # Check if data is a list (direct video data)
            if isinstance(data, list):
                logger.info("Received video data directly", extra={
                    "snapshot_id": snapshot_id,
                    "video_count": len(data),
                    "poll_count": poll_count,
                    "total_wait_time": round(elapsed_time, 1)
                })
                return data
            
            # Check if it's a status response
            if isinstance(data, dict) and 'status' in data:
                status = data['status']
                logger.info(f"Snapshot status: {status}", extra={
                    "snapshot_id": snapshot_id,
                    "status": status,
                    "poll_count": poll_count,
                    "elapsed_seconds": round(elapsed_time, 1)
                })
                
                if status == 'ready':
                    logger.info("Snapshot ready, fetching final data", extra={
                        "snapshot_id": snapshot_id,
                        "total_wait_time": round(elapsed_time, 1)
                    })
                    return self.fetch_snapshot_data(snapshot_id)
                elif status == 'failed':
                    logger.error("Snapshot processing failed", extra={
                        "snapshot_id": snapshot_id,
                        "response": data,
                        "total_wait_time": round(elapsed_time, 1)
                    })
                    raise BrightDataAPIError(f"Snapshot processing failed: {data}")
                else:
                    logger.debug("Snapshot still processing, waiting...", extra={
                        "snapshot_id": snapshot_id,
                        "status": status
                    })
                    time.sleep(10)
            else:
                logger.warning("Unexpected response format during polling", extra={
                    "snapshot_id": snapshot_id,
                    "response_type": type(data).__name__,
                    "response": data,
                    "poll_count": poll_count
                })
                # Wait a bit and continue polling for unexpected formats
                time.sleep(10)
        
        logger.error("Timeout waiting for snapshot", extra={
            "snapshot_id": snapshot_id,
            "max_wait_time": max_wait_time,
            "poll_count": poll_count,
            "elapsed_seconds": round(time.time() - start_time, 1)
        })
        raise BrightDataTimeoutError(f"Timeout waiting for snapshot {snapshot_id} after {max_wait_time}s")
    
    def fetch_snapshot_data(self, snapshot_id):
        """Fetch the actual data from a ready snapshot"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/snapshot/{snapshot_id}?format=json"
        
        logger.info("Fetching final snapshot data", extra={
            "snapshot_id": snapshot_id,
            "url": url
        })
        
        self._log_request("GET", url, headers)
        request_start_time = time.time()
        
        response = requests.get(url, headers=headers)
        self._log_response(response, request_start_time)
        
        try:
            data = response.json()
            logger.info("Successfully fetched snapshot data", extra={
                "snapshot_id": snapshot_id,
                "data_type": type(data).__name__,
                "data_length": len(data) if isinstance(data, list) else None,
                "data_size_bytes": len(response.content)
            })
            return data
        except requests.exceptions.JSONDecodeError as e:
            logger.error("JSON decode error in final data fetch", extra={
                "error": str(e),
                "status_code": response.status_code,
                "response_text": response.text[:500],
                "snapshot_id": snapshot_id
            })
            raise BrightDataAPIError(f"JSON decode error in final fetch: {str(e)}")
    
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