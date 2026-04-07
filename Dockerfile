# Institutional-Grade v11.1.4 "Grandmaster" Dockerfile
FROM python:3.10-slim

# Set environment variables for absolute operational safety
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Establisih the operational directory
WORKDIR /app

# Install system dependencies for high-performance ML modules
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install for deterministic execution
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Sovereign Architecture
COPY . .

# Initiate the High-Fidelity Monitor
CMD ["python", "main.py"]
