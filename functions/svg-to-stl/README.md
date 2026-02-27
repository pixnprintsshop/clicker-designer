# SVG to STL (Cloud Run)

HTTP service that converts an SVG from a URL into an STL file with configurable **scale** and **thickness** (extrusion height).

## API

- **GET /** – Service info and usage
- **GET /convert?url=&lt;svg_url&gt;&amp;scale=&lt;number&gt;&amp;thickness=&lt;number&gt;** – Convert SVG to STL

### Query parameters

| Param       | Required | Default | Description                          |
|------------|----------|---------|--------------------------------------|
| `url`      | Yes      | —       | URL of the SVG (http or https)       |
| `scale`    | No       | 1.0     | Uniform scale factor (0.01–1000)      |
| `thickness`| No       | 1.0     | Extrusion height in SVG units (0.01–1000) |

### Example

```bash
curl -o model.stl "https://YOUR_SERVICE_URL/convert?url=https://example.com/icon.svg&scale=10&thickness=2"
```

## Deploy to Google Cloud Run

### Option 1: Cloud Build (from this directory)

```bash
cd functions/svg-to-stl
gcloud builds submit --config=cloudbuild.yaml .
```

### Option 2: Build and push image yourself

```bash
cd functions/svg-to-stl
export PROJECT_ID=your-gcp-project-id
./deploy.sh
```

## Local run

```bash
cd functions/svg-to-stl
pip install -r requirements.txt
./run.sh
# or: python -m uvicorn app:app --reload --port 8080
```

Then:

```bash
curl -o out.stl "http://localhost:8080/convert?url=https://example.com/icon.svg&thickness=2&scale=1"
```

## How it works

- Fetches the SVG from the given URL
- Writes an OpenSCAD script: `scale([s,s,1]) linear_extrude(height=thickness) import("input.svg")`
- Runs **OpenSCAD** headless to export STL (solid, correct normals)
- Returns the binary STL

Requires OpenSCAD in the container (installed in the Dockerfile).
