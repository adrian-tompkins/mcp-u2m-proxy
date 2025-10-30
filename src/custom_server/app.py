"""
MCP Proxy Server - Main Application
Proxies requests to an upstream MCP server with U2M OAuth authentication
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager

from .oauth_manager import OAuthManager
from .auth import register_auth_routes
from .proxy import register_proxy_routes


STATIC_DIR = Path(__file__).parent / "static"

# Configuration for the upstream MCP server
UPSTREAM_MCP_URL = os.getenv("UPSTREAM_MCP_URL", "https://mcp.atlassian.com/v1")
CALLBACK_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8000"))

# Global OAuth manager
oauth_manager: OAuthManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize OAuth manager on startup"""
    global oauth_manager
    
    print("\nInitializing MCP Proxy Server...")
    print(f"Upstream MCP Server: {UPSTREAM_MCP_URL}")
    print(f"OAuth Callback Port: {CALLBACK_PORT}")
    print(f"Visit http://localhost:{CALLBACK_PORT}/ to authenticate\n")
    
    # Initialize OAuth manager (but don't authenticate yet)
    oauth_manager = OAuthManager(
        server_url=UPSTREAM_MCP_URL,
        callback_port=CALLBACK_PORT,
        client_name="MCP Databricks Proxy"
    )
    
    # Register auth and proxy routes with the initialized oauth_manager
    register_auth_routes(app, oauth_manager, UPSTREAM_MCP_URL)
    register_proxy_routes(app, oauth_manager, UPSTREAM_MCP_URL)
    
    yield
    
    # Cleanup
    print("\nShutting down MCP Proxy Server...")


# Create FastAPI app
app = FastAPI(lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the main web UI"""
    return FileResponse(STATIC_DIR / "index.html")
