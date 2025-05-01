FROM python:3.11.7-slim

# Install system dependencies
RUN apt-get update -y \
    && apt-get install -y \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies including development dependencies
COPY requirements.txt requirements_dev.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt -r requirements_dev.txt

# Copy application code
COPY . .

EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/signals/search || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
