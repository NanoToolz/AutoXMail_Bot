FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Copy requirements
COPY config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directories with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chmod 777 /app/data /app/logs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run bot
CMD ["python", "-u", "src/main.py"]
