# MCP U2M Proxy Server

This is an **OAuth-enabled MCP proxy server** that can be deployed on Databricks Apps or run locally. It proxies requests to upstream MCP servers that require User-to-Machine (U2M) OAuth authentication, automatically handling the OAuth flow with browser-based user authentication.

## Features

- 🔐 **OAuth 2.0 PKCE Authentication** - Secure browser-based user authentication
- 🔄 **Automatic Token Refresh** - Seamlessly handles token expiration with proactive refresh (users stay authenticated long-term)
- ⏰ **Long-Lived Sessions** - Requests `offline_access` scope for persistent refresh tokens
- 🌐 **Full MCP Protocol Support** - Proxies SSE, messages, and all MCP endpoints (including versioned endpoints like `/v1/sse`, `/v2/sse`, etc.)
- 🌉 **Protocol Bridge** - Translates between Streamable HTTP clients and SSE-only upstream servers using MCP SDK
- 💾 **Persistent Token Storage** - Saves credentials for reuse
- 👥 **Multi-User Support** - Manages separate authentication for each user via headers
- 🎨 **Beautiful Auth UI** - Clean OAuth callback pages
- 🚀 **Databricks Apps Ready** - Can be deployed as a Databricks App

## Use Cases

This proxy is perfect for:
- Connecting to OAuth-protected MCP servers
- Centralizing authentication for multiple clients
- Deploying MCP access as a service on Databricks
- Development and testing of OAuth-enabled MCP integrations
- Multi-user environments where each user needs their own authentication

## Multi-User Support

The proxy supports **per-user authentication**, allowing multiple users to use the same proxy instance with their own credentials.

### How It Works

1. **User Identification**: The proxy identifies users via the `X-Forwarded-User` header
2. **Separate Tokens**: Each user gets their own OAuth tokens stored in `~/.mcp/auth/{user_id}/`
3. **Isolated Sessions**: Users authenticate independently and can't access each other's sessions
4. **Automatic Fallback**: When no `X-Forwarded-User` header is present (e.g., local development), the proxy uses a `default` user

### Usage

**With Databricks Apps or similar frameworks:**
```bash
# The framework automatically sets the X-Forwarded-User header
curl -H "X-Forwarded-User: alice@example.com" http://localhost:8000/sse
```

**Local development (no header needed):**
```bash
# Uses 'default' user automatically
curl http://localhost:8000/sse
```

### Token Storage

Tokens are stored per-user:
```
~/.mcp/auth/
  ├── default/                    # Local development user
  │   ├── abc123_tokens.json      # Access & refresh tokens
  │   ├── abc123_client.json      # OAuth client info
  │   └── abc123_auth_state.json  # OAuth state (temporary, during auth)
  ├── alice@example.com/          # User alice
  │   ├── abc123_tokens.json
  │   ├── abc123_client.json
  │   └── abc123_auth_state.json
  └── bob@example.com/            # User bob
      ├── abc123_tokens.json
      ├── abc123_client.json
      └── abc123_auth_state.json
```

## Prerequisites

- Python 3.11+ or Databricks Apps environment
- Databricks CLI (for Databricks deployment)
- `uv` (recommended) or `pip`

## Quick Start (Local Development)

### 1. Configure the Upstream Server

Set the upstream MCP server URL:

```bash
export UPSTREAM_MCP_URL="https://your-mcp-server.com/v1"
export OAUTH_CALLBACK_PORT="8000"  # optional, defaults to 8000
export DEBUG="1"  # optional, enables detailed debug logging

# For deployed environments (Databricks Apps, etc.)
export OAUTH_REDIRECT_URL="https://your-app-url.com/oauth/callback"
```

**Environment Variables:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `UPSTREAM_MCP_URL` | ✅ Yes | - | The base URL of the upstream MCP server (with or without `/sse` suffix) |
| `OAUTH_CALLBACK_PORT` | No | `8000` | Port for OAuth callbacks and the web server (local dev only) |
| `OAUTH_REDIRECT_URL` | No | `http://localhost:{port}/oauth/callback` | Full OAuth callback URL for deployed environments |
| `DEBUG` | No | Not set | Enable debug logging. Set to `1`, `true`, `yes`, or `on` |

**Important for Deployed Environments:**
- When deploying to Databricks Apps or other platforms, you **must** set `OAUTH_REDIRECT_URL` to your app's public URL
- Example: `OAUTH_REDIRECT_URL=https://your-app.databricksapps.com/oauth/callback`
- This ensures OAuth callbacks reach your deployed app instead of localhost

**Logging:**

The proxy uses Python's standard `logging` framework with different log levels:
- **DEBUG**: Detailed request/response information, headers, streaming chunks
- **INFO**: Important events (auth success, registration, token refresh)
- **WARNING**: Non-critical issues (browser auto-open failed)
- **ERROR**: Errors that need attention (auth failures, token refresh failures)

Set `DEBUG=1` to see detailed debug logs. Without it, only INFO level and above are shown.

### 2. Install Dependencies

```bash
uv sync
# or
pip install -r requirements.txt
```

### 3. Start the Proxy Server

```bash
# Using the main module
python -m custom_server.main

# Or with uvicorn
uvicorn custom_server.app:app --host 0.0.0.0 --port 8000
```

### 4. Authenticate

Open your browser and navigate to:

```
http://localhost:8000/
```

You'll see a beautiful web interface with:
- ✅ Current authentication status
- 🔐 "Authenticate" button to start OAuth flow
- 📡 Available MCP endpoints (once authenticated)
- 🗑️ "Clear Credentials" button to re-authenticate

Click the **"Authenticate with Upstream Server"** button, and the proxy will:
1. Open a new window for OAuth authentication
2. Wait for you to log in and authorize
3. Save tokens automatically
4. Show you're ready to use the proxy

### 5. Use the Proxy

Your proxy is now ready! Connect MCP clients to:
- **SSE endpoint**: `http://localhost:8000/sse`
- **Message endpoint**: `http://localhost:8000/message`

**Example with Claude Desktop:**

```json
{
  "mcpServers": {
    "mcp-proxy": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## Local Development

- run `uv` sync:

```bash
uv sync
```

- start the server locally. Changes will trigger a reload:

```bash
uvicorn custom_server.app:app --reload
```

## Deploying a custom MCP server on Databricks Apps

There are two ways to deploy the server on Databricks Apps: using the `databricks apps` CLI or using the `databricks bundle` CLI. Depending on your preference, you can choose either method.

Both approaches require first configuring Databricks authentication:
```bash
export DATABRICKS_CONFIG_PROFILE=<your-profile-name> # e.g. custom-mcp-server
databricks auth login --profile "$DATABRICKS_CONFIG_PROFILE"
```

### Using `databricks apps` CLI

To deploy the server using the `databricks apps` CLI, follow these steps:

1. Create a Databricks app to host your MCP server:
```bash
databricks apps create mcp-custom-server
```

2. Set the required environment variables for your app:
```bash
# Set the upstream MCP server URL
databricks apps update mcp-custom-server --set-env UPSTREAM_MCP_URL="https://your-mcp-server.com/v1"

# IMPORTANT: Set the OAuth redirect URL to your app's URL
# Get your app URL first, then set the redirect URL
APP_URL=$(databricks apps get mcp-custom-server | jq -r .url)
databricks apps update mcp-custom-server --set-env OAUTH_REDIRECT_URL="${APP_URL}/oauth/callback"
```

3. Upload the source code to Databricks and deploy the app:
```bash
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
databricks sync . "/Users/$DATABRICKS_USERNAME/my-mcp-server"
databricks apps deploy mcp-custom-server --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/my-mcp-server"
```

### Using `databricks bundle` CLI

To deploy the server using the `databricks bundle` CLI, follow these steps

[//]: # (TODO: would be nice to also be able to use the same uv command to auto-install dependencies and run the app)
Update the `app.yaml` file in this directory to use the following command:
```yaml
command: ["uvicorn", "custom_server.app:app"]
```

- In this directory, run the following command to deploy and run the MCP server on Databricks Apps:

```bash
uv build --wheel
databricks bundle deploy
databricks bundle run custom-mcp-server
```

## Protocol Bridge: Streamable HTTP ↔ SSE

The proxy includes a **protocol bridge** that allows Streamable HTTP clients to connect to SSE-only upstream servers.

### Problem It Solves

- **Your Client**: Only supports Streamable HTTP (`POST /mcp` with streaming responses)
- **Upstream Server**: Only supports SSE (`GET /sse` for events + `POST /message` for requests)
- **Solution**: The proxy translates between the two protocols automatically!

### How to Use It

**Streamable HTTP Client → `/mcp` endpoint:**

```python
# Client connects to the proxy using Streamable HTTP
client = MCPClient(url="http://localhost:8000/mcp", transport="streamable-http")

# Proxy translates to SSE for the upstream server
# All MCP operations work transparently
tools = await client.list_tools()
result = await client.call_tool("my_tool", {"arg": "value"})
```

### Supported Endpoints

| Client Type | Endpoint | Upstream Translation |
|-------------|----------|---------------------|
| **Streamable HTTP** | `POST /mcp` | → SSE (`GET /sse` + `POST /message`) |
| **SSE** | `GET /sse` | → Direct proxy to upstream |
| **SSE** | `POST /message` | → Direct proxy to upstream |

### How It Works

1. **Client sends** JSON-RPC request to `POST /mcp`
2. **Proxy maintains** persistent SSE connection to upstream (one per user)
3. **Proxy forwards** request via `POST /message` to upstream
4. **Proxy receives** response via SSE stream
5. **Proxy returns** response to client as streaming HTTP

### Supported MCP Methods

The bridge supports all standard MCP methods:
- ✅ `initialize` - Initialize the session
- ✅ `tools/list` - List available tools
- ✅ `tools/call` - Call a tool
- ✅ `resources/list` - List resources
- ✅ `resources/read` - Read a resource
- ✅ `prompts/list` - List prompts
- ✅ `prompts/get` - Get a prompt

### Per-User Sessions

The bridge maintains separate MCP sessions for each user (identified by `X-Forwarded-User` header), ensuring:
- 🔒 Isolated authentication per user
- 🔄 Persistent connections for efficiency
- 🚀 Low latency after initial connection

## Connecting to the MCP Proxy

### Deployed on Databricks Apps

When deployed on Databricks Apps, you can connect using either:

**SSE endpoint (recommended for SSE-capable clients):**
```
https://your-app-url.databricksapps.com/sse
```

**Streamable HTTP endpoint (for Streamable HTTP-only clients):**
```
https://your-app-url.databricksapps.com/mcp
```

**Important Notes for Databricks Deployment:**

1. **OAuth Callback:** When running on Databricks Apps, the OAuth callback URL will be based on your app's public URL. Make sure this URL is accessible for the OAuth provider.

2. **Token Persistence:** Tokens are stored per-user in the `~/.mcp/auth/{user_id}/` directory. On Databricks Apps, ensure this directory persists across app restarts, or implement a different storage mechanism (e.g., Databricks secrets).

3. **Multi-User Support:** The proxy automatically uses the `X-Forwarded-User` header that Databricks Apps provides. Each user will authenticate separately via the web UI (`http://your-app-url/`).

4. **First-Time Authentication:** Users authenticate on-demand via the web UI. No pre-authentication needed.

### Local Development

For local development, you can connect using either:

**SSE endpoint:**
```
http://localhost:8000/sse
```

**Streamable HTTP endpoint:**
```
http://localhost:8000/mcp
```

### Example Client Configurations

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "mcp-via-proxy": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

**Using mcp-remote:**

```bash
npx mcp-remote http://localhost:8000/sse
```

## How OAuth Authentication Works

The proxy implements the OAuth 2.0 Authorization Code flow with PKCE:

1. **User Identification:** Extracts user ID from `X-Forwarded-User` header (or uses "default" for local dev)
2. **Client Registration:** On first run per user, the proxy registers itself as an OAuth client with the upstream server
3. **Authorization:** Opens a browser for user authentication and authorization, requesting `offline_access` scope for long-lived sessions
4. **Token Exchange:** Exchanges the authorization code for access and refresh tokens
5. **Token Storage:** Securely stores tokens per-user in `~/.mcp/auth/{user_id}/`
6. **Auto-Refresh:** Automatically refreshes expired access tokens using refresh tokens (proactively refreshes 5 minutes before expiration)
7. **Request Proxying:** Adds the correct user's Bearer token to all proxied requests

### How Long Do Users Stay Authenticated?

**Short answer: Indefinitely** (as long as the upstream OAuth server allows)

The proxy uses **refresh tokens** to automatically renew access tokens without requiring the user to re-authenticate:

- **Access tokens** typically expire after 1 hour (set by the upstream server)
- **Refresh tokens** are long-lived and can last for weeks, months, or indefinitely (depending on upstream server settings)
- The proxy proactively refreshes access tokens **5 minutes before expiration**, ensuring uninterrupted service
- Users only need to authenticate once, and the proxy handles all subsequent token renewals automatically
- The `offline_access` scope is requested to get persistent refresh tokens that don't expire

**When would a user need to re-authenticate?**
- If they manually clear credentials via the web UI
- If the refresh token itself expires (rare with `offline_access` scope)
- If the upstream OAuth server revokes the token
- If the token storage is deleted (e.g., server restart without persistent storage)

**Token Storage Location:**

Tokens are stored per-user to enable multi-user support:

```
~/.mcp/auth/
├── default/                             # Default user (local development)
│   ├── <server_hash>_tokens.json       # Access & refresh tokens
│   ├── <server_hash>_client_info.json  # OAuth client registration
│   └── <server_hash>_auth_state.json   # OAuth state (during auth flow)
├── alice@example.com/                   # User alice
│   ├── <server_hash>_tokens.json
│   ├── <server_hash>_client_info.json
│   └── <server_hash>_auth_state.json
└── bob@example.com/                     # User bob
    ├── <server_hash>_tokens.json
    ├── <server_hash>_client_info.json
    └── <server_hash>_auth_state.json
```

**Note:** The `auth_state.json` file is temporary and only exists during an active OAuth flow. It's automatically cleaned up after successful authentication.

## Architecture

```
┌─────────────┐         ┌──────────────────────────────┐         ┌──────────────┐
│  MCP Client │◄───────►│      MCP Proxy               │◄───────►│   Upstream   │
│  (Claude)   │   HTTP  │  (Multi-User Support)        │  OAuth  │  MCP Server  │
└─────────────┘         │                              │         └──────────────┘
  X-Forwarded-User      │  ┌──────────┐  ┌──────────┐ │
      Header            │  │  User A  │  │  User B  │ │
                        │  │  Tokens  │  │  Tokens  │ │
                        │  └──────────┘  └──────────┘ │
                        └──────────────────────────────┘
                              │
                              │ OAuth Flow (Per User)
                              ▼
                        ┌──────────────┐
                        │    Browser   │
                        │   (User Auth)│
                        └──────────────┘
```

The proxy automatically:
1. Identifies users via `X-Forwarded-User` header (or uses "default" for local dev)
2. Manages separate OAuth tokens for each user
3. Routes requests to the upstream server with the correct user's credentials
4. Supports any versioned MCP endpoints (`/v1/sse`, `/v2/message`, etc.)

## Troubleshooting

### Invalid State Parameter Error

```
Authentication Failed: Invalid state parameter - possible CSRF attack
```

This error occurs when the OAuth state doesn't match between auth initiation and callback. This is now **automatically fixed** by persisting the OAuth state to disk.

**Why this happened:** In deployed environments (like Databricks Apps), the application might restart or reload between when you start authentication and when the OAuth callback is received. The new version persists the OAuth state (`~/.mcp/auth/{user_id}/auth_state.json`) so it survives restarts.

**If you still see this error:**
1. Ensure the storage directory (`~/.mcp/auth/`) is writable and persists across restarts
2. Clear credentials and try again
3. Check that you're not using multiple load-balanced instances without shared storage

### Browser Doesn't Open

If the browser doesn't open automatically:

```
Could not open browser automatically
```

**Solution:** Copy the authorization URL from the terminal and paste it into your browser.

### Authentication Timeout

```
✗ Authentication failed: Authentication timeout after 300 seconds
```

**Solution:** Complete the OAuth flow within 5 minutes, or restart the server and try again.

### Token Expired

```
HTTPException: 401 - Authentication required
```

**Solution:** The proxy automatically refreshes tokens, so this error is rare. If it occurs:

1. **Check if refresh token is available**: Look for logs indicating "No refresh token available"
2. **Try making another request**: The proxy will attempt to refresh on the next request
3. **Check upstream server status**: The OAuth server might be down or the refresh token was revoked
4. **Re-authenticate**: If refresh fails, visit `http://localhost:8000/` and click "Clear Credentials", then re-authenticate

**Note:** With the improved token refresh logic, users should stay authenticated indefinitely unless there's an issue with the upstream OAuth server.

### Connection Refused to Upstream

```
httpx.ConnectError: Connection refused
```

**Solution:** Verify `UPSTREAM_MCP_URL` is correct and the server is accessible.

### Multi-User Authentication Issues

If users are experiencing authentication issues:

1. **Check the user identifier**: Ensure `X-Forwarded-User` header is being set correctly
2. **Check per-user tokens**: Each user has their own tokens in `~/.mcp/auth/{user_id}/`
3. **Clear user credentials**: Navigate to `http://localhost:8000/` and click "Clear Credentials"
4. **Check logs**: Enable debug mode with `DEBUG=1` to see which user_id is being used for each request
