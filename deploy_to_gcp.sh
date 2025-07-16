#!/bin/bash

# YouTube Discovery Agent - GCP Deployment Script
# This script sets up Cloud SQL, Cloud Storage, Secrets, and deploys to Cloud Run

set -e  # Exit on any error

# Configuration
PROJECT_ID="culture-db-chronicle"  # Unique project ID
REGION="us-central1"
SERVICE_NAME="youtube-discovery"
DB_INSTANCE_NAME="youtube-discovery-db"
DB_NAME="youtube_discovery"
DB_USER="postgres"
DB_PASSWORD="yt_chronicle_db2025"  # Generate secure password
BUCKET_NAME="youtube-discovery"

echo "🚀 YouTube Discovery Agent - GCP Deployment"
echo "=============================================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Step 1: Create and configure project
echo "📋 Step 1: Setting up GCP Project..."
gcloud config set project $PROJECT_ID


# Get connection details
DB_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(connectionName)")
DB_PUBLIC_IP=$(gcloud sql instances describe $DB_INSTANCE_NAME --format="value(ipAddresses[0].ipAddress)")

echo "✅ Cloud SQL instance created"
echo "   Connection Name: $DB_CONNECTION_NAME"
echo "   Public IP: $DB_PUBLIC_IP"

# Step 8: Deploy to Cloud Run
echo "🚀 Step 8: Deploying to Cloud Run..."

gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600s \
    --max-instances 10 \
    --set-env-vars="DB_HOST=$DB_PUBLIC_IP,DB_NAME=$DB_NAME,DB_USER=$DB_USER,STORAGE_BUCKET_NAME=$BUCKET_NAME,BRIGHT_DATA_API_URL=https://api.brightdata.com/datasets/v3/trigger,BRIGHT_DATA_DATASET_ID=gd_lk56epmy2i5g7lzu0k" \
    --set-secrets="DB_PASSWORD=db-password:latest,BRIGHT_DATA_API_KEY=bright-data-key:latest,GEMINI_API_KEY=gemini-key:latest" \
    --allow-unauthenticated \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo "Service URL: $SERVICE_URL"
echo "Database: $DB_CONNECTION_NAME"
echo "Storage: gs://$BUCKET_NAME"
echo ""
echo "🧪 Test your deployment:"
echo "curl $SERVICE_URL/health"
echo ""
echo "🔄 Start discovery:"
echo "curl -X POST $SERVICE_URL/discover"
echo ""
echo "📊 Check status:"
echo "curl $SERVICE_URL/status"
echo ""
echo "📝 View logs:"
echo "gcloud run logs tail $SERVICE_NAME --region=$REGION"
echo ""
echo "💾 Important credentials saved to .env file"
echo ""

# Save deployment info
cat > deployment_info.txt << EOF
YouTube Discovery Agent - Deployment Info
==========================================
Date: $(date)
Project ID: $PROJECT_ID
Region: $REGION
Service URL: $SERVICE_URL
Database: $DB_CONNECTION_NAME ($DB_PUBLIC_IP)
Storage: gs://$BUCKET_NAME
Database Password: $DB_PASSWORD

Commands:
- View logs: gcloud run logs tail $SERVICE_NAME --region=$REGION
- Update service: gcloud run deploy $SERVICE_NAME --source . --region=$REGION
- Delete project: gcloud projects delete $PROJECT_ID
EOF

echo "📋 Deployment info saved to deployment_info.txt"
echo ""
echo "⚠️  Important: Save your database password: $DB_PASSWORD" 