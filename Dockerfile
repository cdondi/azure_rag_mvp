FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY services.py .
COPY .env .

# Copy frontend files
COPY templates/ ./templates/
COPY static/ ./static/

# Copy data files (optional - for offline operation)
COPY chunks_with_embeddings.json .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]