FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer-cached)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py mcp_client.py ./

# Copy the vendored yahoo-finance-mcp MCP server
COPY vendor/ ./vendor/

EXPOSE 8082

CMD ["python", "app.py"]
