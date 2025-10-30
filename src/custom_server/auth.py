"""
Authentication endpoints and helpers for the MCP proxy server
"""
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from urllib.parse import parse_qs

from .templates import oauth_success_template, oauth_error_template
from .logger import logger


async def check_auth_status(oauth_manager):
    """Check if authentication is valid"""
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


def register_auth_routes(app, get_user_id_fn, get_oauth_manager_fn, upstream_url: str):
    """Register authentication routes on the FastAPI app"""
    
    @app.get("/api/auth/status")
    async def get_auth_status(request: Request):
        """Get current authentication status"""
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        
        is_authenticated = await check_auth_status(oauth_manager)
        
        response = {
            "authenticated": is_authenticated,
            "upstream_url": upstream_url,
            "user_id": user_id,
        }
        
        if is_authenticated:
            tokens = oauth_manager.load_tokens()
            client_info = oauth_manager.load_client_info()
            response["client_id"] = client_info.get("client_id") if client_info else None
            response["expires_at"] = tokens.get("expires_at") if tokens else None
        
        return response
    
    
    @app.post("/api/auth/start")
    async def start_auth(request: Request):
        """Start OAuth authentication flow"""
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        
        try:
            # Register client if needed
            await oauth_manager.register_client()
            
            # Start auth flow
            auth_url = await oauth_manager.start_auth_flow()
            
            logger.info(f"Authentication initiated from web UI for user: {user_id}")
            logger.debug(f"Authorization URL: {auth_url}")
            
            return {
                "success": True,
                "auth_url": auth_url,
                "message": "Opening browser for authentication...",
                "user_id": user_id
            }
        except Exception as e:
            logger.error(f"Error starting auth for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @app.post("/api/auth/clear")
    async def clear_auth(request: Request):
        """Clear saved credentials"""
        user_id = get_user_id_fn(request)
        oauth_manager = get_oauth_manager_fn(user_id)
        
        try:
            oauth_manager.clear_credentials()
            logger.info(f"Credentials cleared from web UI for user: {user_id}")
            return {
                "success": True,
                "message": "Credentials cleared successfully",
                "user_id": user_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    
    @app.get("/oauth/callback", include_in_schema=False)
    async def oauth_callback(request: Request):
        """Handle OAuth callback"""
        user_id = get_user_id_fn(request)
        
        # Try to get user_id from state parameter if not in headers
        query_string = str(request.url).split("?", 1)[1] if "?" in str(request.url) else ""
        query_params = parse_qs(query_string)
        
        # If user_id is 'default' (no header), try to get it from state
        # The state format could be: "state_value|user_id"
        if user_id == "default" and "state" in query_params:
            state = query_params["state"][0]
            if "|" in state:
                # Extract user_id from state
                _, state_user_id = state.rsplit("|", 1)
                user_id = state_user_id
                logger.debug(f"Extracted user_id from state: {user_id}")
        
        oauth_manager = get_oauth_manager_fn(user_id)
        result = oauth_manager.handle_callback(query_params)
        
        # If successful, exchange code for tokens
        if result["status"] == "success":
            try:
                code = oauth_manager.auth_code
                await oauth_manager.exchange_code_for_tokens(code)
                logger.info(f"OAuth authentication completed successfully for user: {user_id}")
            except Exception as e:
                logger.error(f"Failed to exchange code for tokens for user {user_id}: {e}")
                result = {
                    "status": "error",
                    "message": f"Failed to complete authentication: {e}"
                }
        
        # Return appropriate HTML response
        if result["status"] == "success":
            html_content = oauth_success_template(f"{result['message']} (user: {user_id})")
        else:
            html_content = oauth_error_template(result["message"])
        
        return HTMLResponse(content=html_content)

