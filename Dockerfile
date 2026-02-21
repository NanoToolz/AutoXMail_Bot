FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY *.py .

# Create non-root user
RUN adduser -D -u 1000 -s /sbin/nologin botuser && \
    mkdir -p /app/data /app/logs && \
    chown -R botuser:botuser /app

# Switch to non-root
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run bot
CMD ["python", "-u", "main.py"]
