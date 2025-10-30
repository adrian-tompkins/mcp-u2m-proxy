from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, Response
import httpx
import asyncio
import os
from urllib.parse import parse_qs
from contextlib import asynccontextmanager

from .oauth_manager import OAuthManager

STATIC_DIR = Path(__file__).parent / "static"

# Configuration for the upstream MCP server
UPSTREAM_MCP_URL = os.getenv("UPSTREAM_MCP_URL", "https://mcp.atlassian.com/v1")
CALLBACK_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8000"))

# Global OAuth manager
oauth_manager: OAuthManager = None
auth_initialized = False
auth_lock = asyncio.Lock()


async def check_auth_status():
    """Check if authentication is valid"""
    global oauth_manager
    
    if not oauth_manager:
        return False
    
    tokens = oauth_manager.load_tokens()
    if not tokens:
        return False
    
    try:
        await oauth_manager.get_valid_access_token()
        return True
    except Exception:
        return False


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
    
    yield
    
    # Cleanup
    print("\nShutting down MCP Proxy Server...")


app = FastAPI(lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/auth/status")
async def get_auth_status():
    """Get current authentication status"""
    is_authenticated = await check_auth_status()
    
    response = {
        "authenticated": is_authenticated,
        "upstream_url": UPSTREAM_MCP_URL,
    }
    
    if is_authenticated:
        tokens = oauth_manager.load_tokens()
        client_info = oauth_manager.load_client_info()
        response["client_id"] = client_info.get("client_id") if client_info else None
        response["expires_at"] = tokens.get("expires_at") if tokens else None
    
    return response


@app.post("/api/auth/start")
async def start_auth():
    """Start OAuth authentication flow"""
    try:
        # Register client if needed
        await oauth_manager.register_client()
        
        # Start auth flow
        auth_url = await oauth_manager.start_auth_flow()
        
        print(f"\nAuthentication initiated from web UI")
        print(f"Authorization URL: {auth_url}\n")
        
        return {
            "success": True,
            "auth_url": auth_url,
            "message": "Opening browser for authentication..."
        }
    except Exception as e:
        print(f"Error starting auth: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/auth/clear")
async def clear_auth():
    """Clear saved credentials"""
    try:
        oauth_manager.clear_credentials()
        print("\nCredentials cleared from web UI\n")
        return {
            "success": True,
            "message": "Credentials cleared successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/oauth/callback", include_in_schema=False)
async def oauth_callback(request: Request):
    """Handle OAuth callback"""
    query_string = str(request.url).split("?", 1)[1] if "?" in str(request.url) else ""
    query_params = parse_qs(query_string)
    
    result = oauth_manager.handle_callback(query_params)
    
    # If successful, exchange code for tokens
    if result["status"] == "success":
        try:
            code = oauth_manager.auth_code
            await oauth_manager.exchange_code_for_tokens(code)
            print("✓ OAuth authentication completed successfully\n")
        except Exception as e:
            print(f"✗ Failed to exchange code for tokens: {e}\n")
            result = {
                "status": "error",
                "message": f"Failed to complete authentication: {e}"
            }
    
    if result["status"] == "success":
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 500px;
                }}
                .success-icon {{
                    font-size: 4rem;
                    color: #10b981;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #6b7280;
                    font-size: 1.1rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✓</div>
                <h1>Authentication Successful!</h1>
                <p>{result["message"]}</p>
                <p style="margin-top: 2rem; font-size: 0.9rem;">
                    The proxy server is now authenticated and ready to use.
                </p>
            </div>
        </body>
        </html>
        """
    else:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 500px;
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #ef4444;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #6b7280;
                    font-size: 1.1rem;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">✗</div>
                <h1>Authentication Failed</h1>
                <p>{result["message"]}</p>
            </div>
        </body>
        </html>
        """
    
    return HTMLResponse(content=html_content)


async def _proxy_sse_handler(request: Request):
    """Shared SSE proxy handler logic"""
    print(f"\n[SSE] Incoming request: {request.method} {request.url.path}")
    print(f"[SSE] Query params: {dict(request.query_params)}")
    print(f"[SSE] Headers: {dict(request.headers)}")
    
    # Check authentication
    if not await check_auth_status():
        raise HTTPException(
            status_code=401, 
            detail="Authentication required. Please visit http://localhost:8000/ to authenticate."
        )
    
    # Get access token
    try:
        access_token = await oauth_manager.get_valid_access_token()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication required: {e}")
    
    # Read request body if present (for POST requests)
    body = None
    if request.method == "POST":
        body = await request.body()
        print(f"[SSE] Request body: {body[:200] if body else None}")
    
    # Construct upstream URL
    upstream_url = f"{UPSTREAM_MCP_URL}/sse"
    print(f"[SSE] Proxying to: {upstream_url} (method: {request.method}, has_body: {body is not None})")
    
    # Prepare headers
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in ["host", "authorization", "content-length"]
    }
    headers["Authorization"] = f"Bearer {access_token}"
    
    # For POST requests, check status first (they return complete responses)
    # For GET requests (SSE), stream directly (they're long-lived connections)
    if request.method == "POST":
        # POST requests return complete responses, so we can check status first
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                request.method,
                upstream_url,
                headers=headers,
                params=request.query_params,
                content=body,
            )
            
            print(f"[SSE] Upstream response status: {response.status_code}")
            print(f"[SSE] Upstream response headers: {dict(response.headers)}")
            
            # If error, return it immediately with proper headers
            if response.status_code >= 400:
                error_text = response.text
                print(f"[SSE] Upstream error ({response.status_code}): {error_text}")
                print(f"[SSE] Returning error to client for fallback")
                
                # Return the error response exactly as received from upstream
                return Response(
                    content=error_text,
                    status_code=response.status_code,
                    headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]},
                )
            
            # If success, return the response
            print(f"[SSE] POST successful, returning response")
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]},
            )
    else:
        # GET requests are SSE connections - stream directly without checking first
        print(f"[SSE] GET request - setting up SSE streaming...")
        
        async def stream_from_upstream():
            async with httpx.AsyncClient(timeout=None) as stream_client:
                async with stream_client.stream(
                    request.method,
                    upstream_url,
                    headers=headers,
                    params=request.query_params,
                    content=body,
                ) as stream_response:
                    print(f"[SSE] Upstream response status: {stream_response.status_code}")
                    
                    # If error, we can't really handle it here after headers are sent
                    # But at least log it
                    if stream_response.status_code >= 400:
                        error_body = await stream_response.aread()
                        error_text = error_body.decode('utf-8', errors='ignore')
                        print(f"[SSE] Upstream error ({stream_response.status_code}): {error_text}")
                        return
                    
                    chunk_count = 0
                    async for chunk in stream_response.aiter_bytes():
                        chunk_count += 1
                        if chunk_count <= 3:
                            print(f"[SSE] Streaming chunk {chunk_count}: {len(chunk)} bytes")
                        yield chunk
                    
                    print(f"[SSE] Finished streaming {chunk_count} chunks")
        
        return StreamingResponse(
            stream_from_upstream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )




# Proxy SSE endpoint (both with and without /v1 prefix)
@app.api_route("/sse", methods=["GET", "POST"])
async def proxy_sse(request: Request):
    """Proxy SSE connections to upstream MCP server"""
    return await _proxy_sse_handler(request)


@app.api_route("/v1/sse", methods=["GET", "POST"])
async def proxy_sse_v1(request: Request):
    """Proxy SSE connections to upstream MCP server (v1 prefix)"""
    return await _proxy_sse_handler(request)


async def _proxy_message_handler(request: Request):
    """Shared message proxy handler logic"""
    print(f"\n[MESSAGE] Incoming request: {request.method} {request.url.path}")
    
    # Check authentication
    if not await check_auth_status():
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please visit http://localhost:8000/ to authenticate."
        )
    
    # Get access token
    try:
        access_token = await oauth_manager.get_valid_access_token()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication required: {e}")
    
    body = await request.body()
    
    # Construct upstream URL
    upstream_url = f"{UPSTREAM_MCP_URL}/message"
    print(f"[MESSAGE] Proxying to: {upstream_url}")
    
    # Prepare headers with OAuth token
    headers = {
        "Content-Type": request.headers.get("content-type", "application/json"),
        "Authorization": f"Bearer {access_token}",
        **{k: v for k, v in request.headers.items() 
           if k.lower() not in ["host", "content-length", "content-type", "authorization"]}
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                upstream_url,
                content=body,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Try refreshing token
                try:
                    new_token = await oauth_manager.refresh_access_token()
                    headers["Authorization"] = f"Bearer {new_token['access_token']}"
                    response = await client.post(
                        upstream_url,
                        content=body,
                        headers=headers,
                    )
                    response.raise_for_status()
                except Exception:
                    raise HTTPException(status_code=401, detail="Authentication failed - please restart server")
            else:
                raise
        
        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )


# Proxy POST endpoint for messages (both with and without /v1 prefix)
@app.post("/message")
async def proxy_message(request: Request):
    """Proxy POST requests to upstream MCP server"""
    return await _proxy_message_handler(request)


@app.post("/v1/message")
async def proxy_message_v1(request: Request):
    """Proxy POST requests to upstream MCP server (v1 prefix)"""
    return await _proxy_message_handler(request)


# Generic proxy for other endpoints
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_all(request: Request, path: str):
    """Proxy all other requests to upstream MCP server"""
    print(f"\n[PROXY_ALL] Incoming request: {request.method} {request.url.path} (captured path: {path})")
    
    # Skip paths that have dedicated handlers
    skip_paths = ["oauth/", "api/", "sse", "message", "v1/sse", "v1/message", ""]
    if any(path.startswith(p) if p.endswith("/") else path == p for p in skip_paths):
        print(f"[PROXY_ALL] Skipping path: {path}")
        raise HTTPException(status_code=404, detail="Not found")
    
    # Check authentication
    if not await check_auth_status():
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please visit http://localhost:8000/ to authenticate."
        )
    
    # Get access token
    try:
        access_token = await oauth_manager.get_valid_access_token()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication required: {e}")
    
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
    
    # Prepare headers with OAuth token
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in ["host", "content-length", "authorization"]
    }
    headers["Authorization"] = f"Bearer {access_token}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=f"{UPSTREAM_MCP_URL}/{path}",
                content=body,
                params=request.query_params,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Try refreshing token
                try:
                    new_token = await oauth_manager.refresh_access_token()
                    headers["Authorization"] = f"Bearer {new_token['access_token']}"
                    response = await client.request(
                        method=request.method,
                        url=f"{UPSTREAM_MCP_URL}/{path}",
                        content=body,
                        params=request.query_params,
                        headers=headers,
                    )
                    response.raise_for_status()
                except Exception:
                    raise HTTPException(status_code=401, detail="Authentication failed - please restart server")
            else:
                raise
        
        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            media_type=response.headers.get("content-type"),
        )