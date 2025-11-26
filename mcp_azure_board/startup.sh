#!/bin/bash
set -e
export PYTHONPATH=$(pwd)
export AZURE_BOARD_MCP=1
exec uvicorn mcp_server_fastapi:app --host 0.0.0.0 --port 8080