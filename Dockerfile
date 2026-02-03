# --- Builder stage (только если нужны C-зависимости) ---
FROM python:3.9-slim as builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# --- Final stage ---
FROM python:3.9-slim
WORKDIR /app

# Устанавливаем только runtime зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Создаем не-root пользователя
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/data && \
    chown -R botuser:botuser /app

# Копируем зависимости и код
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --chown=botuser:botuser . .

USER botuser
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=60s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('data/finance.db') else 1)"

CMD ["python", "bot.py"]
