# Use Python 3.11 slim base image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    netcat-openbsd \
    xmlstarlet \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy test scripts and configuration
COPY tests/ ./tests/
COPY pytest.ini .
COPY run_training_orchestrator_tests.sh .

# Set environment variables for Kubernetes service discovery
ENV TRAINING_ORCHESTRATOR_URL=http://training-orchestrator:8000
ENV ML_ENGINE_URL=http://ml-engine:5000
ENV MODEL_REGISTRY_URL=http://model-registry:8080
ENV QUERY_PARSER_URL=http://query-parser:5001
ENV DB_CONNECTOR_URL=http://db-connector:8081
ENV TEST_SERVICE_URL=http://test-service:8001

# Set Kafka environment variables
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Set PostgreSQL environment variables for testing
ENV DATABASE_URL=postgresql://postgres:password@postgres:5432/training_db

# Configure logging to stdout for Kubernetes
ENV PYTHONUNBUFFERED=1

# Create non-root user for security and make script executable
RUN useradd --create-home --shell /bin/bash testuser && \
    chmod +x run_training_orchestrator_tests.sh
USER testuser

# Default command to run tests
CMD ["pytest", "-v", "--tb=short", "./tests/"]