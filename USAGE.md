# MCP U2M Proxy - Usage Guide

This proxy server enables you to connect to upstream MCP servers that require User-to-Machine (U2M) OAuth authentication. It handles the OAuth flow with browser-based authentication and forwards authenticated requests to the upstream server.

## Features

- 🔐 **OAuth 2.0 PKCE Flow** - Secure browser-based authentication
- 🔄 **Automatic Token Refresh** - Seamlessly refreshes expired tokens
- 💾 **Persistent Token Storage** - Saves tokens locally for reuse
- 🌐 **Full Proxy Support** - Forwards all MCP protocol requests (SSE, messages, etc.)
- 🎨 **Beautiful Auth UI** - Clean success/error pages for OAuth callback

## Configuration

The proxy can be configured via environment variables:

```bash
# The upstream MCP server URL (required)
export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"

# The port for OAuth callback (default: 8000)
export OAUTH_CALLBACK_PORT="8000"
```

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv pip install -r requirements.txt

# Or using pip
pip install -r requirements.txt
```

### 2. Run the Proxy Server

```bash
# Start the server
python -m custom_server.main

# Or with uvicorn directly
uvicorn custom_server.app:app --host 0.0.0.0 --port 8000
```

### 3. Authenticate

When you first run the server, it will:

1. ✓ Check for existing valid tokens
2. ✓ If not found, automatically open your browser for authentication
3. ✓ Wait for you to complete OAuth flow
4. ✓ Save tokens for future use

You'll see output like:

```
============================================================
MCP Proxy Server - OAuth Authentication Required
============================================================

Authentication Steps:
------------------------------------------------------------
1. Opening browser for authentication...
2. Please log in and authorize the application
3. You will be redirected back to this server
------------------------------------------------------------

Authorization URL: https://mcp.atlassian.com/v1/oauth/authorize?...

Waiting for authorization callback...
```

After authentication in the browser, you'll see:

```
✓ Authentication successful!
============================================================
```

### 4. Use the Proxy

Once authenticated, your proxy server is ready! It will:

- Accept MCP protocol requests on `http://localhost:8000`
- Forward them to the upstream server with OAuth authentication
- Automatically refresh tokens when they expire

## Endpoints

### Main Endpoints

- `GET /` - Serves the static index page
- `GET /sse` - Server-Sent Events endpoint (for MCP streaming)
- `POST /message` - Message endpoint (for MCP requests/responses)
- `GET /oauth/callback` - OAuth callback handler (internal use)

### Health Check

You can check if the server is running:

```bash
curl http://localhost:8000/
```

## Token Management

Tokens are stored in `~/.mcp/auth/` with filenames based on the server URL hash:

```
~/.mcp/auth/
├── <server_hash>_tokens.json        # OAuth tokens
└── <server_hash>_client_info.json   # OAuth client registration
```

### Clear Saved Credentials

If you need to re-authenticate (e.g., to use a different account):

```python
from custom_server.oauth_manager import OAuthManager

oauth = OAuthManager(server_url="https://mcp.atlassian.com/v1")
oauth.clear_credentials()
```

Or manually delete the files:

```bash
rm -rf ~/.mcp/auth/
```

## Connecting from MCP Clients

### Using with Claude Desktop

Update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "atlassian-proxy": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

### Using with mcp-remote

```bash
npx mcp-remote http://localhost:8000/sse
```

## Deployment

### Databricks Apps

The proxy includes Databricks Apps configuration files:

1. **app.yaml** - Databricks app configuration
2. **databricks.yml** - Workspace configuration
3. **hooks/apps_build.py** - Build hook for deployment

Deploy with:

```bash
databricks apps deploy
```

### Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"
ENV OAUTH_CALLBACK_PORT="8000"

EXPOSE 8000

CMD ["uvicorn", "custom_server.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t mcp-proxy .
docker run -p 8000:8000 \
  -e UPSTREAM_MCP_URL="https://your-server.com/v1" \
  -v ~/.mcp:/root/.mcp \
  mcp-proxy
```

**Note:** When running in Docker, you'll need to handle the OAuth flow carefully:
- The browser must be able to reach `http://localhost:8000/oauth/callback`
- Consider using a network mode that allows this, or deploy with a public URL

## Troubleshooting

### Authentication Timeout

If authentication takes longer than 5 minutes:

```
✗ Authentication failed: Authentication timeout after 300 seconds
```

**Solution:** Restart the server and complete the OAuth flow more quickly.

### Token Expired

If you see 401 errors:

```
HTTPException: 401 - Authentication required: Token expired and refresh failed
```

**Solution:** The proxy will automatically try to refresh. If that fails, delete credentials and re-authenticate:

```bash
rm -rf ~/.mcp/auth/
python -m custom_server.main
```

### Browser Doesn't Open

If the browser doesn't open automatically:

```
Could not open browser automatically. Please copy and paste the URL above into your browser.
```

**Solution:** Copy the authorization URL from the terminal and paste it into your browser manually.

### Connection Refused

If you can't connect to the upstream server:

```
httpx.ConnectError: [Errno 61] Connection refused
```

**Solution:** 
- Verify `UPSTREAM_MCP_URL` is correct
- Check your network connectivity
- Ensure the upstream server is running

### Invalid Client

If you see "invalid_client" errors:

**Solution:** The OAuth client registration might be invalid. Clear credentials and re-register:

```bash
rm ~/.mcp/auth/<server_hash>_client_info.json
```

Then restart the server.

## Advanced Usage

### Custom OAuth Parameters

Modify `oauth_manager.py` to customize OAuth behavior:

```python
oauth_manager = OAuthManager(
    server_url=UPSTREAM_MCP_URL,
    callback_port=CALLBACK_PORT,
    client_name="My Custom Proxy",
    config_dir=Path.home() / ".my_custom_dir"
)
```

### Add Custom Headers

You can modify the proxy endpoints to add custom headers to all requests:

```python
headers = {
    "Authorization": f"Bearer {access_token}",
    "X-Custom-Header": "my-value",
    **{k: v for k, v in request.headers.items() if ...}
}
```

### Logging

Enable debug logging by modifying the print statements in `oauth_manager.py` or add proper logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

## Security Considerations

1. **Token Storage:** Tokens are stored in plaintext in `~/.mcp/auth/`. Ensure this directory has appropriate permissions.

2. **HTTPS:** When deploying publicly, always use HTTPS. The OAuth callback URL should use HTTPS in production.

3. **Redirect URI:** The callback port must match the port the server is running on. For production, register a permanent redirect URI with your OAuth provider.

4. **Token Refresh:** The proxy automatically refreshes tokens. Monitor for refresh failures which may indicate revoked access.

## Contributing

To add support for additional MCP features:

1. Add new endpoints to `app.py`
2. Ensure they include OAuth authentication via `ensure_authenticated()`
3. Include token refresh logic for 401 errors
4. Test with the upstream server

## License

See LICENSE file for details.

