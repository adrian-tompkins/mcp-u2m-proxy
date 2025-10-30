"""
OAuth Manager for U2M authentication with MCP servers
Handles browser-based OAuth flow with PKCE
"""
import asyncio
import hashlib
import json
import os
import secrets
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode, parse_qs, urlparse
import httpx
from datetime import datetime, timedelta


class OAuthManager:
    """Manages OAuth authentication flow for MCP server"""
    
    def __init__(
        self,
        server_url: str,
        callback_port: int = 3000,
        client_name: str = "MCP Proxy",
        config_dir: Optional[Path] = None
    ):
        self.server_url = server_url.rstrip("/")
        self.callback_port = callback_port
        self.client_name = client_name
        
        # Create config directory for storing tokens
        if config_dir is None:
            config_dir = Path.home() / ".mcp" / "auth"
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Hash server URL for file naming
        self.server_hash = hashlib.sha256(server_url.encode()).hexdigest()[:16]
        
        # OAuth state
        self.state = secrets.token_urlsafe(32)
        self.code_verifier = secrets.token_urlsafe(64)
        self.code_challenge = self._generate_code_challenge(self.code_verifier)
        
        # Client info
        self.client_info: Optional[Dict[str, Any]] = None
        self.tokens: Optional[Dict[str, Any]] = None
        
        # Auth code received from callback
        self.auth_code: Optional[str] = None
        self.auth_code_event = asyncio.Event()
    
    def _generate_code_challenge(self, verifier: str) -> str:
        """Generate PKCE code challenge from verifier"""
        import base64
        digest = hashlib.sha256(verifier.encode()).digest()
        # Base64 URL-safe encoding, remove padding
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    @property
    def redirect_uri(self) -> str:
        """OAuth redirect URI"""
        return f"http://localhost:{self.callback_port}/oauth/callback"
    
    @property
    def client_metadata(self) -> Dict[str, Any]:
        """OAuth client metadata"""
        return {
            "redirect_uris": [self.redirect_uri],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": self.client_name,
            "client_uri": "https://github.com/modelcontextprotocol",
        }
    
    # Token storage
    def _get_file_path(self, filename: str) -> Path:
        """Get path for config file"""
        return self.config_dir / f"{self.server_hash}_{filename}"
    
    def _load_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load JSON from file"""
        path = self._get_file_path(filename)
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None
    
    def _save_json(self, filename: str, data: Dict[str, Any]) -> None:
        """Save JSON to file"""
        path = self._get_file_path(filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    
    def load_tokens(self) -> Optional[Dict[str, Any]]:
        """Load saved OAuth tokens"""
        tokens = self._load_json("tokens.json")
        if tokens:
            # Check if tokens are expired
            expires_at = tokens.get("expires_at")
            if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                return None
        self.tokens = tokens
        return tokens
    
    def save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save OAuth tokens"""
        # Calculate expiration time
        if "expires_in" in tokens:
            expires_at = datetime.now() + timedelta(seconds=tokens["expires_in"])
            tokens["expires_at"] = expires_at.isoformat()
        
        self.tokens = tokens
        self._save_json("tokens.json", tokens)
    
    def load_client_info(self) -> Optional[Dict[str, Any]]:
        """Load saved client information"""
        self.client_info = self._load_json("client_info.json")
        return self.client_info
    
    def save_client_info(self, client_info: Dict[str, Any]) -> None:
        """Save client information"""
        self.client_info = client_info
        self._save_json("client_info.json", client_info)
    
    def clear_credentials(self) -> None:
        """Clear all saved credentials"""
        for filename in ["tokens.json", "client_info.json"]:
            path = self._get_file_path(filename)
            if path.exists():
                path.unlink()
        self.tokens = None
        self.client_info = None
    
    async def _discover_oauth_endpoints(self) -> Dict[str, Any]:
        """Discover OAuth endpoints from server"""
        # Parse the server URL to get the base domain
        from urllib.parse import urlparse
        parsed = urlparse(self.server_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        async with httpx.AsyncClient() as client:
            # Try well-known endpoint at the root domain first
            well_known_urls = [
                f"{base_url}/.well-known/oauth-authorization-server",
                f"{self.server_url}/.well-known/oauth-authorization-server",
            ]
            
            for well_known_url in well_known_urls:
                try:
                    print(f"Trying OAuth discovery at: {well_known_url}")
                    response = await client.get(well_known_url)
                    response.raise_for_status()
                    oauth_config = response.json()
                    print(f"✓ Discovered OAuth endpoints from {well_known_url}")
                    return oauth_config
                except Exception as e:
                    print(f"  Could not discover at {well_known_url}: {e}")
                    continue
            
            # Fallback: try standard endpoints at base domain and server URL
            print(f"Using fallback OAuth endpoint discovery")
            return {
                "registration_endpoint": f"{base_url}/oauth/register",
                "authorization_endpoint": f"{base_url}/oauth/authorize",
                "token_endpoint": f"{base_url}/oauth/token",
            }
    
    # OAuth flow
    async def register_client(self) -> Dict[str, Any]:
        """Register OAuth client with server"""
        # Check if client already registered
        client_info = self.load_client_info()
        if client_info:
            print(f"Using existing client registration: {client_info.get('client_id')}")
            return client_info
        
        # Discover OAuth endpoints
        oauth_config = await self._discover_oauth_endpoints()
        
        # Register client
        registration_endpoint = oauth_config.get("registration_endpoint")
        if not registration_endpoint:
            raise Exception("No registration endpoint found in OAuth configuration")
        
        async with httpx.AsyncClient() as client:
            print(f"Registering OAuth client at: {registration_endpoint}")
            try:
                response = await client.post(registration_endpoint, json=self.client_metadata)
                response.raise_for_status()
                
                client_info = response.json()
                client_info["oauth_config"] = oauth_config
                
                self.save_client_info(client_info)
                print(f"✓ Registered new OAuth client: {client_info.get('client_id')}")
                
                return client_info
            except httpx.HTTPStatusError as e:
                print(f"✗ Registration failed: {e.response.status_code} {e.response.text}")
                raise Exception(
                    f"OAuth client registration failed at {registration_endpoint}: "
                    f"{e.response.status_code} - {e.response.text}"
                )
    
    async def start_auth_flow(self) -> str:
        """Start OAuth authorization flow and return auth URL"""
        # Ensure client is registered
        client_info = await self.register_client()
        oauth_config = client_info.get("oauth_config", {})
        
        # Build authorization URL
        auth_endpoint = oauth_config.get("authorization_endpoint", f"{self.server_url}/oauth/authorize")
        
        params = {
            "client_id": client_info["client_id"],
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": "S256",
            "scope": "openid profile email",
        }
        
        auth_url = f"{auth_endpoint}?{urlencode(params)}"
        return auth_url
    
    def open_browser_for_auth(self, auth_url: str) -> None:
        """Open browser for user authentication"""
        print(f"\nOpening browser for authentication...")
        print(f"If browser doesn't open, visit: {auth_url}\n")
        try:
            webbrowser.open(auth_url)
        except Exception as e:
            print(f"Could not open browser automatically: {e}")
            print(f"Please visit the URL above manually.")
    
    async def wait_for_auth_code(self, timeout: int = 300) -> str:
        """Wait for OAuth callback with authorization code"""
        try:
            await asyncio.wait_for(self.auth_code_event.wait(), timeout=timeout)
            if not self.auth_code:
                raise Exception("No authorization code received")
            return self.auth_code
        except asyncio.TimeoutError:
            raise Exception(f"Authentication timeout after {timeout} seconds")
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens"""
        client_info = self.client_info
        if not client_info:
            raise Exception("Client not registered")
        
        oauth_config = client_info.get("oauth_config", {})
        token_endpoint = oauth_config.get("token_endpoint", f"{self.server_url}/oauth/token")
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": client_info["client_id"],
            "code_verifier": self.code_verifier,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_endpoint, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            self.save_tokens(tokens)
            
            print("Successfully obtained access tokens")
            return tokens
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        if not self.tokens or "refresh_token" not in self.tokens:
            raise Exception("No refresh token available")
        
        client_info = self.client_info
        if not client_info:
            raise Exception("Client not registered")
        
        oauth_config = client_info.get("oauth_config", {})
        token_endpoint = oauth_config.get("token_endpoint", f"{self.server_url}/oauth/token")
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.tokens["refresh_token"],
            "client_id": client_info["client_id"],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(token_endpoint, data=data)
            response.raise_for_status()
            
            tokens = response.json()
            self.save_tokens(tokens)
            
            print("Successfully refreshed access token")
            return tokens
    
    async def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary"""
        # Load existing tokens
        tokens = self.load_tokens()
        
        if not tokens:
            raise Exception("No tokens available - authentication required")
        
        # Check if token is expired
        expires_at = tokens.get("expires_at")
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
            # Try to refresh
            try:
                tokens = await self.refresh_access_token()
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                raise Exception("Token expired and refresh failed - re-authentication required")
        
        return tokens["access_token"]
    
    def handle_callback(self, query_params: Dict[str, Any]) -> Dict[str, str]:
        """Handle OAuth callback with authorization code"""
        # Verify state
        state = query_params.get("state", [""])[0]
        if state != self.state:
            return {
                "status": "error",
                "message": "Invalid state parameter - possible CSRF attack"
            }
        
        # Check for errors
        error = query_params.get("error", [""])[0]
        if error:
            error_description = query_params.get("error_description", ["Unknown error"])[0]
            return {
                "status": "error",
                "message": f"OAuth error: {error} - {error_description}"
            }
        
        # Get authorization code
        code = query_params.get("code", [""])[0]
        if not code:
            return {
                "status": "error",
                "message": "No authorization code received"
            }
        
        # Store code and signal completion
        self.auth_code = code
        self.auth_code_event.set()
        
        return {
            "status": "success",
            "message": "Authorization successful! You can close this window."
        }

