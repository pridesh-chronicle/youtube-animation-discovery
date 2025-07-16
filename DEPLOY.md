# 🚀 YouTube Discovery Agent - GCP Deployment Guide

## **Prerequisites**

1. **Google Cloud SDK** installed: https://cloud.google.com/sdk/docs/install
2. **Docker** installed: https://docs.docker.com/get-docker/
3. **API Keys**:
   - Bright Data API Key: `671f7cc3f2c8797b3cfbb568358ff60b470c3237c781f06d4d70f3967190ecce`
   - Google Gemini API Key: Get from https://makersuite.google.com/app/apikey

## **🎯 One-Command Deployment**

```bash
# Run the automated deployment script
./deploy_to_gcp.sh
```

The script will:
- ✅ Create GCP project
- ✅ Set up Cloud SQL database
- ✅ Create Cloud Storage bucket
- ✅ Configure secrets
- ✅ Deploy to Cloud Run
- ✅ Generate local .env file

## **📋 Manual Steps Required**

1. **Enable Billing**: When prompted, visit the billing URL and link a billing account
2. **Provide API Keys**: Enter your Bright Data and Gemini API keys when asked

## **🧪 Testing Your Deployment**

Once deployed, you'll get a service URL. Test it:

```bash
# Health check
curl https://your-service-url/health

# Start discovery (async)
curl -X POST https://your-service-url/discover \
  -H "Content-Type: application/json" \
  -d '{
    "seed_videos": ["hwiyUuYZLHE", "RtU8nBnpFVE"],
    "max_iterations": 10,
    "save_videos": true
  }'

# Check status
curl https://your-service-url/status

# View logs
curl https://your-service-url/logs?count=20
```

## **📊 API Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API documentation |
| `/health` | GET | Health check |
| `/status` | GET | Discovery status |
| `/discover` | POST | Start async discovery |
| `/discover/sync` | POST | Start sync discovery |
| `/logs` | GET | Get recent logs |

## **🔧 Local Development**

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (uses cloud database)
python cloud_main.py

# Or run original version
python main.py
```

## **💰 Cost Estimates**

- **Cloud SQL (db-f1-micro)**: ~$7-15/month
- **Cloud Storage**: ~$1-5/month (videos)
- **Cloud Run**: ~$0-20/month (usage-based)
- **Total**: ~$8-40/month depending on usage

## **🛠️ Troubleshooting**

### **Build Errors**
```bash
# Test Docker build locally
docker build -t youtube-discovery .
docker run -p 8080:8080 youtube-discovery
```

### **Database Connection Issues**
```bash
# Test database connection
python -c "
from cloud_database import CloudDatabase
db = CloudDatabase()
with db.get_connection() as conn:
    print('✅ Database connected!')
"
```

### **API Key Issues**
Check your secrets:
```bash
gcloud secrets versions access latest --secret="bright-data-key"
gcloud secrets versions access latest --secret="gemini-key"
```

## **📝 View Logs**

```bash
# Cloud Run logs
gcloud run logs tail youtube-discovery --region=us-central1

# Local log analysis
python log_viewer.py summary
python log_viewer.py recent 50
```

## **🗑️ Cleanup**

```bash
# Delete entire project (saves costs)
gcloud projects delete youtube-discovery-TIMESTAMP
```

## **🔄 Updates**

```bash
# Deploy updates
gcloud run deploy youtube-discovery --source . --region=us-central1
```

---

**🎉 Your YouTube Discovery Agent is now running on Google Cloud!** 