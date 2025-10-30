"""
MCP Proxy Server - Main Application
Proxies requests to an upstream MCP server with U2M OAuth authentication
"""
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager
from typing import Dict

from .oauth_manager import OAuthManager
from .auth import register_auth_routes
from .proxy import register_proxy_routes
from .logger import logger


STATIC_DIR = Path(__file__).parent / "static"

# Configuration for the upstream MCP server
UPSTREAM_MCP_URL = os.getenv("UPSTREAM_MCP_URL")
if not UPSTREAM_MCP_URL:
    raise ValueError("UPSTREAM_MCP_URL environment variable must be set")
CALLBACK_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8000"))

# OAuth redirect URL (for deployed environments)
# Format: https://your-app-url.com/oauth/callback
#OAUTH_REDIRECT_URL = f"{os.getenv("DATABRICKS_APP_URL")}/oauth/callback"
#print(f"OAUTH_REDIRECT_URL: {OAUTH_REDIRECT_URL}")
#OAUTH_REDIRECT_URL = "http://localhost:8000/oauth/callback"
OAUTH_REDIRECT_URL = "None/oauth/callback"

# Per-user OAuth managers
oauth_managers: Dict[str, OAuthManager] = {}


def get_user_id_from_request(request: Request) -> str:
    """
    Extract user ID from request headers.
    Uses X-Forwarded-User header if present, otherwise returns 'default'
    """
    user_id = request.headers.get("X-Forwarded-User", "default")
    if user_id != "default":
        logger.debug(f"Request from user: {user_id}")
    return user_id


def get_oauth_manager(user_id: str) -> OAuthManager:
    """
    Get or create an OAuthManager instance for the given user.
    Caches instances to avoid recreating them.
    """
    if user_id not in oauth_managers:
        logger.info(f"Creating new OAuthManager for user: {user_id}")
        oauth_managers[user_id] = OAuthManager(
            server_url=UPSTREAM_MCP_URL,
            callback_port=CALLBACK_PORT,
            client_name="MCP Databricks Proxy",
            user_id=user_id,
            redirect_url=OAUTH_REDIRECT_URL
        )
    return oauth_managers[user_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the proxy server"""
    print("\nInitializing MCP Proxy Server...")
    print(f"Upstream MCP Server: {UPSTREAM_MCP_URL}")
    print(f"OAuth Callback Port: {CALLBACK_PORT}")
    print(f"Multi-user support: enabled (via X-Forwarded-User header)\n")
    
    # Register auth and proxy routes with user management functions
    register_auth_routes(app, get_user_id_from_request, get_oauth_manager, UPSTREAM_MCP_URL)
    register_proxy_routes(app, get_user_id_from_request, get_oauth_manager, UPSTREAM_MCP_URL)
    
    yield
    
    # Cleanup
    print("\nShutting down MCP Proxy Server...")
    print(f"Served {len(oauth_managers)} unique user(s)")


# Create FastAPI app
app = FastAPI(lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve the main web UI"""
    return FileResponse(STATIC_DIR / "index.html")
