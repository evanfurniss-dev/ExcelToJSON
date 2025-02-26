FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for numpy/pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies in the correct order
COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.24.3
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Use the gunicorn config
CMD gunicorn -c gunicorn_config.py app:app 