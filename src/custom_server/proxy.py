"""
Proxy endpoints and handlers for forwarding requests to the upstream MCP server
"""
import re
from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, Response
import httpx

from .auth import check_auth_status
from .logger import logger


async def _proxy_sse_handler(request: Request, oauth_manager, upstream_url: str):
    """Shared SSE proxy handler logic"""
    logger.debug(f"[SSE] Incoming request: {request.method} {request.url.path}")
    logger.debug(f"[SSE] Query params: {dict(request.query_params)}")
    logger.debug(f"[SSE] Headers: {dict(request.headers)}")
    
    # Check authentication
    if not await check_auth_status(oauth_manager):
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
        logger.debug(f"[SSE] Request body: {body[:200] if body else None}")
    
    # Construct upstream URL
    sse_url = f"{upstream_url}/sse"
    logger.debug(f"[SSE] Proxying to: {sse_url} (method: {request.method}, has_body: {body is not None})")
    
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
                sse_url,
                headers=headers,
                params=request.query_params,
                content=body,
            )
            
            logger.debug(f"[SSE] Upstream response status: {response.status_code}")
            logger.debug(f"[SSE] Upstream response headers: {dict(response.headers)}")
            
            # If error, return it immediately with proper headers
            if response.status_code >= 400:
                error_text = response.text
                logger.info(f"[SSE] Upstream error ({response.status_code}): {error_text}")
                logger.debug(f"[SSE] Returning error to client for fallback")
                
                # Return the error response exactly as received from upstream
                return Response(
                    content=error_text,
                    status_code=response.status_code,
                    headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]},
                )
            
            # If success, return the response
            logger.debug(f"[SSE] POST successful, returning response")
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]},
            )
    else:
        # GET requests are SSE connections - stream directly without checking first
        logger.debug(f"[SSE] GET request - setting up SSE streaming...")
        
        async def stream_from_upstream():
            async with httpx.AsyncClient(timeout=None) as stream_client:
                async with stream_client.stream(
                    request.method,
                    sse_url,
                    headers=headers,
                    params=request.query_params,
                    content=body,
                ) as stream_response:
                    logger.debug(f"[SSE] Upstream response status: {stream_response.status_code}")
                    
                    # If error, we can't really handle it here after headers are sent
                    # But at least log it
                    if stream_response.status_code >= 400:
                        error_body = await stream_response.aread()
                        error_text = error_body.decode('utf-8', errors='ignore')
                        logger.error(f"[SSE] Upstream error ({stream_response.status_code}): {error_text}")
                        return
                    
                    chunk_count = 0
                    async for chunk in stream_response.aiter_bytes():
                        chunk_count += 1
                        if chunk_count <= 3:
                            logger.debug(f"[SSE] Streaming chunk {chunk_count}: {len(chunk)} bytes")
                        yield chunk
                    
                    logger.debug(f"[SSE] Finished streaming {chunk_count} chunks")
        
        return StreamingResponse(
            stream_from_upstream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )


async def _proxy_message_handler(request: Request, oauth_manager, upstream_url: str):
    """Shared message proxy handler logic"""
    logger.debug(f"[MESSAGE] Incoming request: {request.method} {request.url.path}")
    
    # Check authentication
    if not await check_auth_status(oauth_manager):
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
    message_url = f"{upstream_url}/message"
    logger.debug(f"[MESSAGE] Proxying to: {message_url}")
    
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
                message_url,
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
                        message_url,
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


def register_proxy_routes(app, get_user_id_fn, get_oauth_manager_fn, upstream_url: str):
    """Register proxy routes on the FastAPI app"""
    
    # Proxy SSE endpoint (without version prefix)
    @app.api_route("/sse", methods=["GET", "POST"])
    async def proxy_sse(request: Request):
        """Proxy SSE connections to upstream MCP server"""
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        return await _proxy_sse_handler(request, oauth_manager, upstream_url)
    
    
    # Proxy SSE endpoint (with version prefix - supports v1, v2, v3, etc.)
    @app.api_route("/v{version:int}/sse", methods=["GET", "POST"])
    async def proxy_sse_versioned(version: int, request: Request):
        """Proxy SSE connections to upstream MCP server (versioned)"""
        logger.debug(f"[SSE] Request for version v{version}")
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        return await _proxy_sse_handler(request, oauth_manager, upstream_url)
    
    
    # Proxy POST endpoint for messages (without version prefix)
    @app.post("/message")
    async def proxy_message(request: Request):
        """Proxy POST requests to upstream MCP server"""
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        return await _proxy_message_handler(request, oauth_manager, upstream_url)
    
    
    # Proxy POST endpoint for messages (with version prefix - supports v1, v2, v3, etc.)
    @app.post("/v{version:int}/message")
    async def proxy_message_versioned(version: int, request: Request):
        """Proxy POST requests to upstream MCP server (versioned)"""
        logger.debug(f"[MESSAGE] Request for version v{version}")
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        return await _proxy_message_handler(request, oauth_manager, upstream_url)
    
    
    # Generic proxy for other endpoints
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_all(request: Request, path: str):
        """Proxy all other requests to upstream MCP server"""
        logger.debug(f"[PROXY_ALL] Incoming request: {request.method} {request.url.path} (captured path: {path})")
        
        # Skip paths that have dedicated handlers
        skip_paths = ["oauth/", "api/", "sse", "message", ""]
        
        # Check static skip paths
        if any(path.startswith(p) if p.endswith("/") else path == p for p in skip_paths):
            logger.debug(f"[PROXY_ALL] Skipping path: {path}")
            raise HTTPException(status_code=404, detail="Not found")
        
        # Check versioned endpoints (v1/sse, v2/message, v99/sse, etc.)
        if re.match(r'^v\d+/(sse|message)$', path):
            logger.debug(f"[PROXY_ALL] Skipping versioned path: {path}")
            raise HTTPException(status_code=404, detail="Not found")
        
        # Get user-specific oauth manager
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        
        # Check authentication
        if not await check_auth_status(oauth_manager):
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
                    url=f"{upstream_url}/{path}",
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
                            url=f"{upstream_url}/{path}",
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

