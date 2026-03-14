# Stage 1: Build Go bridge
FROM golang:1.25-bookworm AS go-builder

WORKDIR /build
COPY whatsapp-bridge/ ./
RUN CGO_ENABLED=1 GOOS=linux go build -o whatsapp-bridge .

# Stage 2: Final image with Python MCP server + Go bridge
FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sqlite3 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Go bridge binary
COPY --from=go-builder /build/whatsapp-bridge /usr/local/bin/whatsapp-bridge

# Set up Python MCP server
WORKDIR /app/whatsapp-mcp-server
COPY whatsapp-mcp-server/pyproject.toml whatsapp-mcp-server/uv.lock ./
RUN uv sync --frozen --no-dev

COPY whatsapp-mcp-server/ ./

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create data directory
RUN mkdir -p /data

# Environment variables
ENV DATA_DIR=/data
ENV BRIDGE_PORT=8080
ENV MCP_TRANSPORT=sse
ENV FASTMCP_PORT=8000
ENV MESSAGES_DB_PATH=/data/messages.db
ENV WHATSAPP_API_URL=http://localhost:8080/api

# Expose MCP SSE port and bridge port
EXPOSE 8000 8080

ENTRYPOINT ["/entrypoint.sh"]
