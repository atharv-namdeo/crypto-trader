# Stage 1: Build React Dashboard
FROM node:20-slim AS build-stage
WORKDIR /app
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ ./
RUN npm run build

# Stage 2: Python Engine
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements FIRST for caching
COPY requirements.txt .

# Install Python dependencies with CPU-only optimization for Torch (saves 1.5GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.2.2+cpu --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built dashboard from build-stage
COPY --from=build-stage /app/dist /app/dashboard/dist

# Create necessary directories
RUN mkdir -p logs reports ml/models

# Health check (simplified as requested)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Expose port (FastAPI usually runs on 8000 or 8080)
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
