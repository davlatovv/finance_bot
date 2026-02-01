# Multi-stage build for optimized image size
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements/production.txt requirements/
COPY requirements/base.txt requirements/

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements/production.txt


# Final stage - minimal runtime image
FROM python:3.9-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/data && \
    chown -R botuser:botuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/botuser/.local

# Copy application code
COPY --chown=botuser:botuser . .

# Switch to non-root user
USER botuser

# Add local binaries to PATH
ENV PATH=/home/botuser/.local/bin:$PATH

# Set Python to run in unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('data/finance.db') else 1)"

# Run the bot
CMD ["python", "bot.py"]
