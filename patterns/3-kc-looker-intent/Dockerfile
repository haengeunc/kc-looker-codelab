FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

COPY looker_governed_kc_agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY looker_governed_kc_agent /app/looker_governed_kc_agent
COPY sample_policies /app/sample_policies

# Runtime Environment Variables (override at deploy time)
ENV GOOGLE_GENAI_USE_VERTEXAI=1
ENV GOOGLE_CLOUD_PROJECT=opm-looker-core-demo-instance
ENV GOOGLE_CLOUD_LOCATION=us-central1
ENV LOOKER_BASE_URL=https://looker.cloud-bi-opm.com
ENV LOOKER_CLIENT_ID=B3T44CSKfBXQ7dCWQhjP
ENV LOOKER_CLIENT_SECRET=BpjRy4nq6Q6cJnysjF6SQfm7
ENV LOOKER_MODEL_NAME=thelook_prod
ENV PORT=8080

EXPOSE 8080

# Start ADK Web UI on Cloud Run port ($PORT)
CMD ["sh", "-c", "adk web --host 0.0.0.0 --port ${PORT:-8080} --allow_origins '*'"]
