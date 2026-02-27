#!/bin/bash

# docker build --platform linux/amd64 -t svg-to-stl .
# docker run -p 8080:8080 svg-to-stl

python -m uvicorn app:app --reload --port 8080
