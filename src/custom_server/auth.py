"""
Authentication endpoints and helpers for the MCP proxy server
"""
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
from urllib.parse import parse_qs

from .templates import oauth_success_template, oauth_error_template


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


def register_auth_routes(app, oauth_manager, upstream_url: str):
    """Register authentication routes on the FastAPI app"""
    
    @app.get("/api/auth/status")
    async def get_auth_status():
        """Get current authentication status"""
        is_authenticated = await check_auth_status(oauth_manager)
        
        response = {
            "authenticated": is_authenticated,
            "upstream_url": upstream_url,
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
        
        # Return appropriate HTML response
        if result["status"] == "success":
            html_content = oauth_success_template(result["message"])
        else:
            html_content = oauth_error_template(result["message"])
        
        return HTMLResponse(content=html_content)

