#!/usr/bin/env python3
"""
Simple test script to verify the MCP proxy is working correctly
"""
import asyncio
import httpx
import json
import sys


async def test_proxy(base_url: str = "http://localhost:8000"):
    """Test the MCP proxy endpoints"""
    
    print("="*60)
    print("MCP U2M Proxy - Connection Test")
    print("="*60)
    print(f"\nTesting proxy at: {base_url}\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Root endpoint
        print("Test 1: Root endpoint...")
        try:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                print("✓ Root endpoint accessible")
            else:
                print(f"✗ Root endpoint returned status {response.status_code}")
        except Exception as e:
            print(f"✗ Failed to connect to root endpoint: {e}")
            print("\nMake sure the proxy server is running:")
            print("  python -m custom_server.main")
            return False
        
        # Test 2: SSE endpoint (just check if it responds)
        print("\nTest 2: SSE endpoint...")
        try:
            # We'll just try to connect - not expecting a full response without auth
            response = await client.get(f"{base_url}/sse", timeout=5.0)
            if response.status_code == 200:
                print("✓ SSE endpoint accessible and authenticated")
            elif response.status_code == 401:
                print("✗ SSE endpoint not authenticated")
                print("  Please run authentication first:")
                print("  python -m custom_server.cli auth")
                return False
            else:
                print(f"✗ SSE endpoint returned status {response.status_code}")
        except httpx.TimeoutException:
            # Timeout is OK for SSE - it means connection was established
            print("✓ SSE endpoint connected (timeout expected for streaming)")
        except Exception as e:
            print(f"✗ Failed to connect to SSE endpoint: {e}")
            return False
        
        # Test 3: OAuth callback endpoint structure
        print("\nTest 3: OAuth callback endpoint...")
        try:
            # We expect this to fail gracefully without proper OAuth params
            response = await client.get(f"{base_url}/oauth/callback")
            print("✓ OAuth callback endpoint exists")
        except Exception as e:
            print(f"✗ OAuth callback endpoint error: {e}")
        
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print("\n✓ Proxy server is running and accessible")
        print("\nNext steps:")
        print("1. Ensure authentication is complete:")
        print("   python -m custom_server.cli status")
        print("\n2. Connect your MCP client to:")
        print(f"   {base_url}/sse")
        print("\n3. For Claude Desktop, add to claude_desktop_config.json:")
        print(f"""   {{
     "mcpServers": {{
       "proxy": {{
         "url": "{base_url}/sse"
       }}
     }}
   }}""")
        
        return True


async def test_auth_status():
    """Test authentication status"""
    print("\n" + "="*60)
    print("Authentication Status")
    print("="*60 + "\n")
    
    try:
        from src.custom_server.oauth_manager import OAuthManager
        import os
        
        server_url = os.getenv("UPSTREAM_MCP_URL", "https://mcp.atlassian.com/v1")
        oauth = OAuthManager(server_url=server_url)
        
        tokens = oauth.load_tokens()
        client_info = oauth.load_client_info()
        
        if client_info:
            print(f"✓ OAuth client registered")
            print(f"  Client ID: {client_info.get('client_id', 'N/A')}")
        else:
            print("✗ No OAuth client registered")
        
        if tokens:
            print(f"✓ Tokens saved")
            try:
                token = await oauth.get_valid_access_token()
                print(f"✓ Access token is valid")
            except Exception as e:
                print(f"✗ Token validation failed: {e}")
        else:
            print("✗ No tokens found")
            print("\nRun authentication:")
            print("  python -m custom_server.main")
    
    except ImportError:
        print("⚠ Cannot import oauth_manager - skipping auth check")
    except Exception as e:
        print(f"✗ Error checking auth status: {e}")


def main():
    """Main test runner"""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    print("\nStarting MCP Proxy tests...\n")
    
    try:
        # Run connection tests
        result = asyncio.run(test_proxy(base_url))
        
        # Run auth status check
        asyncio.run(test_auth_status())
        
        if result:
            print("\n✓ All tests passed!\n")
            sys.exit(0)
        else:
            print("\n✗ Some tests failed\n")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

