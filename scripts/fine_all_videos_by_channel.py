import requests

API_KEY = 'AIzaSyCnzlZ1Y_8nFf5U3-J4RGLqmIQRurnR3Yg'
CHANNEL_ID = 'UCv9AWko-S7gc-Oil2MjDbwA'  # example: Google Developers

# Step 1: Get uploads playlist ID
url = f'https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={CHANNEL_ID}&key={API_KEY}'
res = requests.get(url).json()
uploads_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

# Step 2: Get all video IDs from the uploads playlist
video_ids = []
page_token = ''

while True:
    playlist_url = (
        f'https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_id}'
        f'&maxResults=50&pageToken={page_token}&key={API_KEY}'
    )
    res = requests.get(playlist_url).json()
    for item in res['items']:
        video_ids.append(item['contentDetails']['videoId'])
    page_token = res.get('nextPageToken')
    if not page_token:
        break

print(f'Total videos found: {video_ids}')
print(f'Total videos found: {len(video_ids)}')
