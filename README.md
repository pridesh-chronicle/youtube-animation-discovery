# 🎬 YouTube Animation Discovery Agent

An AI-powered system that automatically discovers and catalogs animated YouTube videos using BrightData API for metadata extraction and Google Gemini AI for animation classification. Built with resilient processing, cloud-based queuing, and real-time monitoring.

## ⭐ Key Features

### 🤖 **AI-Powered Classification**
- Google Gemini AI for accurate animation detection
- Handles 2D/3D animation, stop-motion, mixed media
- Intelligent prompting for precise categorization

### 🔄 **Resilient Processing**
- **Retry logic** with exponential backoff (3 attempts)
- **Timeout handling** - API failures don't stop discovery
- **Error recovery** - Failed batches are skipped gracefully
- **Queue persistence** - Survives service restarts

### ☁️ **Cloud-Based Queue**
- PostgreSQL-backed discovery queue
- Multi-instance scalability
- Real-time status tracking
- Automatic cleanup and recovery

### 🌐 **Web API & Monitoring**
- RESTful API with comprehensive endpoints
- Real-time metrics and analytics
- CORS-enabled for frontend integration
- Health monitoring and logging

---

## 🚀 Quick Start

### **Option 1: Traditional Discovery**
```bash
# Start discovery with seed videos
curl -X POST http://your-server:8080/discover \
  -H "Content-Type: application/json" \
  -d '{
    "seed_videos": ["hwiyUuYZLHE", "RtU8nBnpFVE", "tbmVhb1-fPg"],
    "save_videos": false
  }'
```

### **Option 2: Queue-Based Discovery**
```bash
# 1. Add videos to queue
curl -X POST http://your-server:8080/queue/add \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["hwiyUuYZLHE", "RtU8nBnpFVE"]}'

# 2. Start discovery
curl -X POST http://your-server:8080/discover \
  -H "Content-Type: application/json" \
  -d '{"seed_videos": []}'
```

### **Monitor Progress**
```bash
# Check discovery status
curl http://your-server:8080/status

# View metrics
curl http://your-server:8080/metrics

d
```

---

## 📡 API Reference

### **Discovery Management**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/discover` | POST | Start async discovery process |
| `/discover/sync` | POST | Start synchronous discovery (blocks) |
| `/status` | GET | Get real-time discovery status |

### **Metrics & Analytics**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/metrics` | GET | Database metrics & top creators |
| `/health` | GET | System health check |
| `/logs` | GET | Recent discovery logs |

### **Queue Management**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/queue/stats` | GET | Queue statistics & status |
| `/queue/add` | POST | Add videos to discovery queue |
| `/queue/cleanup` | POST | Clean up old queue entries |

### **Development**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cors-test` | GET/POST | CORS functionality test |

---

## 🏗️ Architecture

### **Core Components**

```
