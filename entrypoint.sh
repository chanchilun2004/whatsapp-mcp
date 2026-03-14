#!/bin/bash
set -e

echo "Starting WhatsApp Bridge..."
whatsapp-bridge &
BRIDGE_PID=$!

# Wait for bridge to be ready
echo "Waiting for bridge to start on port ${BRIDGE_PORT:-8080}..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${BRIDGE_PORT:-8080}/api/status" > /dev/null 2>&1; then
        echo "Bridge is ready!"
        break
    fi
    if ! kill -0 $BRIDGE_PID 2>/dev/null; then
        echo "Bridge process died unexpectedly"
        exit 1
    fi
    sleep 1
done

echo "Starting MCP server on port ${FASTMCP_PORT:-8000}..."
cd /app/whatsapp-mcp-server
exec uv run python main.py
