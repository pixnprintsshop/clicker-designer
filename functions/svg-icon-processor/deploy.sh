#!/bin/bash
set -euo pipefail

export PROJECT_ID=clicker-designer

# Configure Docker for gcr.io (one-time, safe to re-run)
gcloud auth configure-docker gcr.io --quiet

# Build and push from the functions directory
docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/svg-icon-processor:latest ../svg-icon-processor
docker push gcr.io/$PROJECT_ID/svg-icon-processor:latest

# Deploy pre-built image to Cloud Run (no Cloud Build needed)
gcloud run deploy svg-icon-processor \
  --image gcr.io/$PROJECT_ID/svg-icon-processor:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --platform managed \
  --project $PROJECT_ID