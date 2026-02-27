# Google Cloud Run: SVG icon processor (Inkscape → mask → Potrace)
FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install Inkscape, Potrace, and dbus (Inkscape needs a session bus)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        inkscape \
        potrace \
        dbus \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application and pipeline scripts
COPY app.py process_mask.py ./

# Cloud Run expects to bind to PORT
EXPOSE 8080
# Cloud Run sets PORT at runtime
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
