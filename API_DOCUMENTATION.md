# Discovery Agent API Documentation

## Base URL
```
http://localhost:8080
```

## Global Query Parameters
All `/metrics/*` endpoints support these optional parameters:

- `include_kids` (boolean): `true` | `false` (default: `true`)
  - Controls whether kids content is included in results
- `time_period` (string): `1d` | `7d` | `1m` | `1y` | `all_time` (default: `all_time`)
  - Filters results by time period for relevant endpoints

## Available Endpoints

### 1. Health Check
```http
GET /health
```
**Response:**
```json
{
    "status": "healthy",
    "cors_enabled": true,
    "discovery_status": "idle",
    "timestamp": "2025-07-23T15:16:08.302738"
}
```

### 2. Database Overview
```http
GET /metrics/overview?include_kids=false
```
**Response:**
```json
{
    "timestamp": "2025-07-23T15:32:57.017879",
    "include_kids": false,
    "database_overview": {
        "total_videos": 4055,
        "total_creators": 1616,
        "total_views": 13270330860
    },
    "discovery_agent_status": "idle",
    "current_queue_size": 0
}
```

### 3. Videos (What I'm Watching Now + Top Videos by Time Period)
```http
GET /metrics/videos?time_period=7d&include_kids=false
```
**Purpose:** This single endpoint provides both:
- **What I'm watching now**: Recent videos discovered (always shows last 5)
- **Top videos by time period**: Filtered by time_period parameter (1d/7d/1m/1y/all_time)

**Response:**
```json
{
    "timestamp": "2025-07-23T15:04:05.503800",
    "include_kids": false,
    "time_period": "7d",
    "recent_videos": [
        {
            "video_id": "ov-2xh4UmtU",
            "title": "The Worst Anime EDP'S",
            "creator": "@thevirginityslayer",
            "views": 28232,
            "discovered_at": "2025-07-18T15:35:07.182952",
            "url": "https://www.youtube.com/watch?v=ov-2xh4UmtU",
            "avatar_img_channel": "https://yt3.ggpht.com/...",
            "preview_image": "https://i.ytimg.com/vi/ov-2xh4UmtU/hqdefault.jpg"
        }
    ],
    "top_videos_7d": [
        {
            "video_id": "xP2tHAXjZhI",
            "title": "How many organs can YOU live without?",
            "creator": "@kurzgesagt",
            "views": 1315603,
            "date_posted": "2025-07-17T14:01:35",
            "url": "https://www.youtube.com/watch?v=xP2tHAXjZhI",
            "avatar_img_channel": "https://yt3.ggpht.com/...",
            "preview_image": "https://i.ytimg.com/vi/xP2tHAXjZhI/hqdefault.jpg"
        }
    ]
}
```
**Note:** 
- `recent_videos`: Always returns last 5 discovered videos (what you're watching now)
- `top_videos_{time_period}`: Returns top 10 videos for the specified time period
- Use different `time_period` values (1d, 7d, 1m, 1y, all_time) to get top videos for different ranges

### 4. Top Creators (Views, Subscribers, Engagement)
```http
GET /metrics/creators?time_period=all_time&include_kids=false
```
**Response:**
```json
{
    "timestamp": "2025-07-23T15:33:13.758325",
    "include_kids": false,
    "time_period": "all_time",
    "top_creators": {
        "by_views": [
            {
                "creator": "@theodd1sout",
                "total_views": 1209352189,
                "video_count": 22,
                "avg_subscribers": 20500000,
                "avatar_img_channel": "https://yt3.ggpht.com/..."
            }
        ],
        "by_subscribers": [
            {
                "creator": "channelUCuVPpxrm2VAgpH3Ktln4HXg",
                "subscribers": 190000000,
                "total_views": 1813991,
                "video_count": 1,
                "avatar_img_channel": "https://yt3.ggpht.com/..."
            }
        ],
        "by_engagement": [
            {
                "creator": "@motiv8minds-20",
                "total_views": 793,
                "total_likes": 8,
                "total_comments": 1,
                "subscribers": 1890000,
                "video_count": 1,
                "engagement_rate": 238336.57,
                "avatar_img_channel": "https://yt3.ggpht.com/..."
            }
        ]
    }
}
```

### 5. Trending Music & Tags
```http
GET /metrics/trending?time_period=all_time&include_kids=false
```
**Response:**
```json
{
    "timestamp": "2025-07-23T15:17:15.123456",
    "include_kids": false,
    "time_period": "all_time",
    "trending_music_all_time": [
        {
            "music": "{\"song\": \"Lord of the Land\", \"artist\": \"Kevin Macleod\"}",
            "usage_count": 7,
            "creator_count": 5,
            "total_views": 2845632
        }
    ],
    "trending_tags_all_time": [
        {
            "tag": "animation",
            "usage_count": 482,
            "creator_count": 156,
            "total_views": 89456321
        }
    ]
}
```

### 6. Up and Coming (Videos & Creators) - 5 Each
```http
GET /metrics/upcoming?include_kids=false
```
**Response:**
```json
{
    "timestamp": "2025-07-23T15:17:49.456789",
    "include_kids": false,
    "up_and_coming": {
        "videos": [
            {
                "video_id": "F7Prpu_PK5M",
                "title": "Every Girl in Our Family is Jealous Of M...",
                "creator": "@MovieCabbage",
                "views": 1776772,
                "date_posted": "2025-07-18T15:32:54.988495",
                "url": "https://www.youtube.com/watch?v=F7Prpu_PK5M",
                "avatar_img_channel": "https://yt3.ggpht.com/...",
                "preview_image": "https://i.ytimg.com/vi/F7Prpu_PK5M/hqdefault.jpg",
                "views_per_day": 335496.16
            }
        ],
        "creators": [
            {
                "creator": "@MovieCabbage",
                "subscribers": 30900,
                "total_views": 1456789,
                "video_count": 12,
                "first_posted": "2025-06-15T10:30:00",
                "latest_posted": "2025-07-20T14:22:11",
                "avatar_img_channel": "https://yt3.ggpht.com/...",
                "velocity": 87110.56
            }
        ]
    }
}
```
**Note:** Returns exactly 5 videos and 5 creators each, filtered for up-and-coming content.

### 7. Queue Status
```http
GET /queue/stats
```
**Response:**
```json
{
    "timestamp": "2025-07-23T15:03:26.333301",
    "discovery_agent_status": "idle",
    "queue_stats": {
        "pending": 5,
        "processing": 0,
        "completed": 0,
        "failed": 0,
        "total": 5
    }
}
```

### 8. Original Comprehensive Metrics (Backward Compatibility)
```http
GET /metrics
```
**Response:** Contains all data in a single response with complete creator metrics, time-based video rankings, and up-and-coming analytics.

## Important Notes

### Content Filtering Changes
- **Kids Content**: Use `include_kids=false` to filter out kids content for general audiences
- **Type Filtering**: All queries now filter for `type = 'ANIMATED'` content (updated from `is_animated = true`)

### Time Periods
- `1d`: Last 24 hours
- `7d`: Last 7 days  
- `1m`: Last 30 days
- `1y`: Last 365 days
- `all_time`: No time restriction

### Response Field Patterns
- Time-specific fields use pattern: `top_videos_{time_period}`, `trending_music_{time_period}`
- All endpoints include `timestamp`, `include_kids` fields
- Time-aware endpoints include `time_period` field

### Updated Limits
- **Up and Coming**: Now returns 5 videos and 5 creators (reduced from 10)
- **Trending Music**: 15 items maximum
- **Trending Tags**: 20 items maximum  
- **Top Videos**: 10 items per time period
- **Top Creators**: 10 items per category (views, subscribers, engagement)

### Performance & Database
- All queries now use `type = 'ANIMATED'` for better performance
- Database queries are optimized with proper indexing
- Each request initializes a fresh database connection
- Response times typically under 500ms for most endpoints

## Example Frontend Integration

```typescript
// Fetch trending content for the past week, no kids content
const trending = await fetch('/metrics/trending?time_period=7d&include_kids=false');
const data = await trending.json();

console.log(data.trending_music_7d); // Music trending in past 7 days
console.log(data.trending_tags_7d);  // Tags trending in past 7 days

// Get up and coming creators and videos (5 each)
const upcoming = await fetch('/metrics/upcoming?include_kids=false');
const upcomingData = await upcoming.json();

console.log(upcomingData.up_and_coming.videos);   // 5 hot new videos
console.log(upcomingData.up_and_coming.creators); // 5 rising creators

// Get comprehensive creator metrics by all ranking methods
const creators = await fetch('/metrics/creators?time_period=all_time&include_kids=false');
const creatorsData = await creators.json();

console.log(creatorsData.top_creators.by_views);       // Top by total views
console.log(creatorsData.top_creators.by_subscribers); // Top by subscriber count  
console.log(creatorsData.top_creators.by_engagement);  // Top by engagement rate
```

## Quick Reference

| Endpoint | Purpose | Key Parameters | Returns |
|----------|---------|----------------|---------|
| `/health` | System status | - | Health check |
| `/metrics/overview` | Database summary | `include_kids` | Total counts |
| `/metrics/videos` | Recent + top videos | `time_period`, `include_kids` | 5 recent + 10 top videos |
| `/metrics/creators` | Creator rankings | `time_period`, `include_kids` | 10 creators each by views, subs, engagement |
| `/metrics/trending` | Music + tags | `time_period`, `include_kids` | 15 music + 20 tags |
| `/metrics/upcoming` | Rising content | `include_kids` | 5 videos + 5 creators |
| `/queue/stats` | Queue status | - | Processing statistics | 