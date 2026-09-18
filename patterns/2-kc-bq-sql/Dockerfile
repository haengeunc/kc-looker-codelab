FROM python:3.13-slim

WORKDIR /app

# Install curl for downloading the MCP Toolbox for Databases binary (optional)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Install MCP Toolbox for Databases binary (toolbox v1.10.0)
RUN curl -fsSL https://storage.googleapis.com/genai-toolbox/v1.10.0/linux/amd64/toolbox -o /usr/local/bin/toolbox \
    && chmod +x /usr/local/bin/toolbox

# Copy agent package and requirements
COPY kc_analyst_agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY kc_analyst_agent /app/kc_analyst_agent

# Cloud Run defaults (override GOOGLE_CLOUD_PROJECT at deploy time)
ENV GOOGLE_GENAI_USE_VERTEXAI=1
ENV GOOGLE_CLOUD_PROJECT=YOUR-GCP-PROJECT
ENV GOOGLE_CLOUD_LOCATION=us-central1
ENV PORT=8080

EXPOSE 8080

# Start ADK Web UI + API Server on Cloud Run port ($PORT)
CMD ["sh", "-c", "adk web --host 0.0.0.0 --port ${PORT:-8080} --allow_origins '*'"]
