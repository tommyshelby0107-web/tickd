# tickd by Sid: one container with everything the app needs, including Tesseract for scanned PDFs.
# Works on any Docker host (Render, Railway, Google Cloud, a VM). The host sets PORT; locally it defaults to 8000.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STORAGE_DIR=/app/storage

# Tesseract OCR (English) for scans; the Python packages ship their own PDF libraries.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-deploy.txt .
RUN pip install -r requirements-deploy.txt

COPY app ./app
COPY static ./static
COPY data ./data
COPY samples ./samples
COPY policy.yaml ./

# The database and uploads live here. It starts from the seed data in data/ on first boot.
RUN mkdir -p /app/storage

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
