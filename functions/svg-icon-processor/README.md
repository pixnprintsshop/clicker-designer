# SVG Icon Processor (Cloud Run)

HTTP service that takes an SVG icon URL, runs the mask pipeline (Inkscape → mask → Potrace), and returns the processed SVG.

## API

- **GET /** – Service info and usage
- **GET /process?url=<svg_url>** – Process an SVG from URL and return the output SVG

Example:

```bash
curl -o result.svg "https://YOUR_SERVICE_URL/process?url=https://api.iconify.design/tabler:zodiac-leo.svg"
```

## Deploy to Google Cloud Run

### Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed and logged in
- A GCP project with Cloud Run and Container Registry (or Artifact Registry) enabled

### Option 1: Deploy from source (recommended)

From the **scripts** directory:

```bash
cd scripts
gcloud run deploy svg-icon-processor \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --platform managed
```

`gcloud` will build the container from the Dockerfile and deploy it. You’ll get a URL like `https://svg-icon-processor-xxxxx-uc.a.run.app`.

### Option 2: Use Cloud Build

From the **scripts** directory:

```bash
cd scripts
gcloud builds submit --config=cloudbuild.yaml .
```

Set the region in `cloudbuild.yaml` via the `_REGION` substitution if needed (default: `us-central1`).

### Option 3: Build and push image yourself

```bash
cd scripts
export PROJECT_ID=your-gcp-project-id
docker build -t gcr.io/$PROJECT_ID/svg-icon-processor:latest .
docker push gcr.io/$PROJECT_ID/svg-icon-processor:latest
gcloud run deploy svg-icon-processor \
  --image gcr.io/$PROJECT_ID/svg-icon-processor:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --platform managed
```

## Local run (Docker)

Requires Docker, and the image includes Inkscape and Potrace:

```bash
cd scripts
docker build -t svg-icon-processor .
docker run -p 8080:8080 svg-icon-processor
```

Then:

```bash
curl -o out.svg "http://localhost:8080/process?url=https://api.iconify.design/tabler:zodiac-leo.svg"
```

## Local run (without Docker)

You need Python 3, Inkscape, and Potrace installed (e.g. `brew install inkscape potrace` on macOS). From `scripts/`:

```bash
pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8080
```

Use the same `curl` as above to test.
