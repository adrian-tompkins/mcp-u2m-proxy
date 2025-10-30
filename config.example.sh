#!/bin/bash
# MCP U2M Proxy Configuration Example
# Copy this file and customize for your environment

# The upstream MCP server URL to proxy requests to
export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"

# The port for OAuth callback
# This must match the port the server is running on
export OAUTH_CALLBACK_PORT="8000"

# Optional: Custom OAuth client name
# This will be displayed to users during the OAuth flow
# export CLIENT_NAME="My MCP Proxy"

# Optional: Custom config directory for storing tokens
# Default: ~/.mcp/auth
# export CONFIG_DIR="/path/to/custom/config"

# Start the server
echo "Starting MCP U2M Proxy with configuration:"
echo "  Upstream URL: $UPSTREAM_MCP_URL"
echo "  Callback Port: $OAUTH_CALLBACK_PORT"
echo ""

# Uncomment to start the server
# python -m custom_server.main

