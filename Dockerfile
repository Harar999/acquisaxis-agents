# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY agent_prompts_*.md ./

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application — bind to Railway's $PORT (fallback 8080)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile - main:app"]
