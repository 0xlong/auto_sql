# ============================================================================
# DOCKERFILE FOR AWS APP RUNNER DEPLOYMENT
# ============================================================================
# This Dockerfile creates a container image that AWS App Runner will use
# to run your Streamlit application. Think of it as a recipe that tells
# Docker how to build a complete, isolated environment for your app.
# ============================================================================

# STEP 1: Choose the base Python image
# We use Python 3.11 slim image - it's smaller and faster than full Python images
# The "slim" variant includes only essential packages, reducing image size
FROM python:3.11-slim

# STEP 2: Set working directory inside the container
# This is where all our application files will be placed
# Think of it as "cd /app" - all commands run from here
WORKDIR /app

# STEP 3: Install system dependencies
# Streamlit and some Python packages need these system libraries to work
# - gcc: Compiler needed for some Python packages
# - curl: For downloading files and health checks
# - git: In case any Python packages need to fetch code from Git
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# STEP 4: Copy dependency file first (Docker layer caching optimization)
# Docker caches each step. By copying requirements.txt first and installing
# dependencies separately, Docker can reuse the cached dependency layer
# even if your code changes. This makes rebuilds much faster.
COPY requirements.txt .

# STEP 5: Install Python dependencies
# Install all packages listed in requirements.txt into the container
# --no-cache-dir: Don't store pip cache (reduces image size)
# --upgrade: Ensure we get latest compatible versions
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# STEP 6: Copy application code
# Copy all your source code, data files, and configuration into the container
# The .dockerignore file (if present) will exclude files we don't need
COPY . .

# STEP 7: Expose the port Streamlit runs on
# Streamlit by default runs on port 8501
# This tells Docker "this container will listen on port 8501"
# AWS App Runner will automatically map this to a public URL
EXPOSE 8501

# STEP 8: Set health check
# AWS App Runner uses this to verify your app is running correctly
# It periodically sends a GET request to /_stcore/health
# If it gets a 200 response, the app is healthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# STEP 9: Set environment variable for Streamlit
# Streamlit needs to know it's running in a server environment (not local)
# This disables some local-only features and enables server mode
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# STEP 10: Run the Streamlit application
# This is the command that starts your app when the container starts
# --server.port: Port to listen on (must match EXPOSE above)
# --server.address: Listen on all network interfaces (0.0.0.0)
# --server.headless: Don't try to open a browser (we're in a container)
# src/app.py: Your main Streamlit application file
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]


