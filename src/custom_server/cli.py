#!/usr/bin/env python3
"""
CLI tool for managing MCP U2M Proxy authentication
"""
import asyncio
import sys
import os
from pathlib import Path
from oauth_manager import OAuthManager


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(text)
    print("="*60 + "\n")


def print_status(emoji: str, text: str):
    """Print a status line"""
    print(f"{emoji} {text}")


async def check_auth_status(server_url: str):
    """Check authentication status"""
    print_header("Authentication Status Check")
    
    oauth = OAuthManager(server_url=server_url)
    
    # Check for saved tokens
    tokens = oauth.load_tokens()
    client_info = oauth.load_client_info()
    
    if not client_info:
        print_status("✗", "No OAuth client registered")
        return False
    
    print_status("✓", f"OAuth Client ID: {client_info.get('client_id', 'N/A')}")
    
    if not tokens:
        print_status("✗", "No tokens saved")
        return False
    
    print_status("✓", "Tokens found")
    
    # Check token validity
    try:
        access_token = await oauth.get_valid_access_token()
        print_status("✓", "Access token is valid")
        print(f"\nToken preview: {access_token[:20]}...")
        return True
    except Exception as e:
        print_status("✗", f"Token validation failed: {e}")
        return False


async def authenticate(server_url: str):
    """Perform authentication"""
    print_header("Starting OAuth Authentication")
    
    oauth = OAuthManager(server_url=server_url)
    
    try:
        # Register client
        print("Step 1: Registering OAuth client...")
        await oauth.register_client()
        print_status("✓", "Client registered")
        
        # Start auth flow
        print("\nStep 2: Starting authorization flow...")
        auth_url = await oauth.start_auth_flow()
        print_status("📋", f"Authorization URL: {auth_url}")
        
        # Open browser
        print("\nStep 3: Opening browser...")
        oauth.open_browser_for_auth(auth_url)
        print_status("🌐", "Browser opened - please complete authentication")
        
        # Wait for callback
        print("\nStep 4: Waiting for OAuth callback...")
        print("(Make sure the proxy server is running to handle the callback)")
        print("Timeout: 300 seconds")
        
        code = await oauth.wait_for_auth_code(timeout=300)
        print_status("✓", "Authorization code received")
        
        # Exchange for tokens
        print("\nStep 5: Exchanging code for tokens...")
        tokens = await oauth.exchange_code_for_tokens(code)
        print_status("✓", "Access tokens obtained")
        
        print_header("Authentication Successful!")
        print(f"Access token saved to: {oauth._get_file_path('tokens.json')}")
        
    except Exception as e:
        print_header("Authentication Failed")
        print_status("✗", str(e))
        return False
    
    return True


async def refresh_token(server_url: str):
    """Refresh access token"""
    print_header("Refreshing Access Token")
    
    oauth = OAuthManager(server_url=server_url)
    
    try:
        tokens = await oauth.refresh_access_token()
        print_status("✓", "Token refreshed successfully")
        print(f"New token preview: {tokens['access_token'][:20]}...")
        return True
    except Exception as e:
        print_status("✗", f"Token refresh failed: {e}")
        return False


def clear_credentials(server_url: str):
    """Clear saved credentials"""
    print_header("Clearing Credentials")
    
    oauth = OAuthManager(server_url=server_url)
    oauth.clear_credentials()
    
    print_status("✓", "All credentials cleared")
    print(f"Deleted files from: {oauth.config_dir}")


def list_credentials():
    """List all saved credentials"""
    print_header("Saved Credentials")
    
    config_dir = Path.home() / ".mcp" / "auth"
    
    if not config_dir.exists():
        print_status("ℹ", "No credentials directory found")
        return
    
    files = sorted(config_dir.glob("*"))
    
    if not files:
        print_status("ℹ", "No saved credentials")
        return
    
    print(f"Location: {config_dir}\n")
    
    for file in files:
        size = file.stat().st_size
        print(f"  • {file.name} ({size} bytes)")


def print_usage():
    """Print usage information"""
    print("""
MCP U2M Proxy - Authentication CLI

Usage:
    python -m custom_server.cli <command> [server_url]

Commands:
    status      Check authentication status
    auth        Perform OAuth authentication
    refresh     Refresh access token
    clear       Clear saved credentials
    list        List all saved credentials
    help        Show this help message

Arguments:
    server_url  The upstream MCP server URL (optional, defaults to env var)
                Default: UPSTREAM_MCP_URL or https://mcp.atlassian.com/v1

Examples:
    # Check authentication status
    python -m custom_server.cli status

    # Authenticate with default server
    python -m custom_server.cli auth

    # Authenticate with custom server
    python -m custom_server.cli auth https://custom-mcp.example.com/v1

    # Refresh token
    python -m custom_server.cli refresh

    # Clear credentials
    python -m custom_server.cli clear

    # List all saved credentials
    python -m custom_server.cli list

Environment Variables:
    UPSTREAM_MCP_URL     Default MCP server URL
    OAUTH_CALLBACK_PORT  OAuth callback port (default: 8000)
""")


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Get server URL from args or env
    server_url = None
    if len(sys.argv) > 2:
        server_url = sys.argv[2]
    else:
        server_url = os.getenv("UPSTREAM_MCP_URL", "https://mcp.atlassian.com/v1")
    
    if command == "help":
        print_usage()
    
    elif command == "status":
        await check_auth_status(server_url)
    
    elif command == "auth":
        print("\n⚠️  WARNING: This command requires the proxy server to be running")
        print("   to handle the OAuth callback. Please start the server first:")
        print("   python -m custom_server.main\n")
        
        response = input("Continue? (y/n): ")
        if response.lower() == 'y':
            await authenticate(server_url)
    
    elif command == "refresh":
        await refresh_token(server_url)
    
    elif command == "clear":
        print("\n⚠️  WARNING: This will delete all saved credentials")
        response = input("Continue? (y/n): ")
        if response.lower() == 'y':
            clear_credentials(server_url)
    
    elif command == "list":
        list_credentials()
    
    else:
        print(f"Unknown command: {command}")
        print("Run 'python -m custom_server.cli help' for usage")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

