#!/bin/bash
set -euo pipefail

export PROJECT_ID=clicker-designer

# Configure Docker for gcr.io (one-time, safe to re-run)
gcloud auth configure-docker gcr.io --quiet

# Build and push from the svg-to-stl directory
docker build --platform linux/amd64 -t gcr.io/$PROJECT_ID/svg-to-stl:latest .
docker push gcr.io/$PROJECT_ID/svg-to-stl:latest

# Deploy pre-built image to Cloud Run (no Cloud Build needed)
gcloud run deploy svg-to-stl \
  --image gcr.io/$PROJECT_ID/svg-to-stl:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --platform managed \
  --project $PROJECT_ID
