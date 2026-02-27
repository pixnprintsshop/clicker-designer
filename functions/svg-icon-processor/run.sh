#!/bin/bash

# docker build --platform linux/amd64 -t svg-icon-processor .
# docker run -p 8080:8080 svg-icon-processor

python -m uvicorn app:app --reload --port 8080