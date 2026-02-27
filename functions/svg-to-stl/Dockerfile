# Google Cloud Run: SVG to STL via OpenSCAD
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# OpenSCAD for import() + linear_extrude() -> STL
RUN apt-get update \
    && apt-get install -y --no-install-recommends openscad \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
