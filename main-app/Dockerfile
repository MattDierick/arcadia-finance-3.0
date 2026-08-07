FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY app.py db.py ./

# Copy frontend (built at Docker build time)
COPY frontend/ ./frontend/

EXPOSE 8080

CMD ["python", "app.py"]
