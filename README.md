# MCP U2M Proxy Server

This is an **OAuth-enabled MCP proxy server** that can be deployed on Databricks Apps or run locally. It proxies requests to upstream MCP servers that require User-to-Machine (U2M) OAuth authentication, automatically handling the OAuth flow with browser-based user authentication.

## Features

- 🔐 **OAuth 2.0 PKCE Authentication** - Secure browser-based user authentication
- 🔄 **Automatic Token Refresh** - Seamlessly handles token expiration
- 🌐 **Full MCP Protocol Support** - Proxies SSE, messages, and all MCP endpoints
- 💾 **Persistent Token Storage** - Saves credentials for reuse
- 🎨 **Beautiful Auth UI** - Clean OAuth callback pages
- 🚀 **Databricks Apps Ready** - Can be deployed as a Databricks App

## Use Cases

This proxy is perfect for:
- Connecting to OAuth-protected MCP servers (e.g., Atlassian MCP)
- Centralizing authentication for multiple clients
- Deploying MCP access as a service on Databricks
- Development and testing of OAuth-enabled MCP integrations

## Prerequisites

- Python 3.11+ or Databricks Apps environment
- Databricks CLI (for Databricks deployment)
- `uv` (recommended) or `pip`

## Quick Start (Local Development)

### 1. Configure the Upstream Server

Set the upstream MCP server URL:

```bash
export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"
export OAUTH_CALLBACK_PORT="8000"  # optional, defaults to 8000
```

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
    "atlassian-proxy": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## CLI Tools

Manage authentication with the built-in CLI:

```bash
# Check authentication status
python -m custom_server.cli status

# Manually trigger authentication
python -m custom_server.cli auth

# Refresh access token
python -m custom_server.cli refresh

# Clear saved credentials
python -m custom_server.cli clear

# List all saved credentials
python -m custom_server.cli list
```

For detailed usage information, see [USAGE.md](USAGE.md).

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

Create a Databricks app to host your MCP server:
```bash
databricks apps create mcp-custom-server
```

Upload the source code to Databricks and deploy the app:

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

## Connecting to the MCP Proxy

### Deployed on Databricks Apps

When deployed on Databricks Apps, connect using the SSE endpoint:

```
https://your-app-url.databricksapps.com/sse
```

**Important Notes for Databricks Deployment:**

1. **OAuth Callback:** When running on Databricks Apps, the OAuth callback URL will be based on your app's public URL. Make sure this URL is accessible for the OAuth provider.

2. **Token Persistence:** Tokens are stored in the `~/.mcp/auth/` directory. On Databricks Apps, ensure this directory persists across app restarts, or implement a different storage mechanism (e.g., Databricks secrets).

3. **First-Time Authentication:** You may need to manually trigger the OAuth flow on first deployment. Consider these options:
   - Use the CLI tool to pre-authenticate before deployment
   - Implement a health check endpoint that triggers auth
   - Use Databricks secrets to pre-populate tokens

### Local Development

For local development or when the proxy is running locally:

```
http://localhost:8000/sse
```

### Example Client Configurations

**Claude Desktop (`claude_desktop_config.json`):**

```json
{
  "mcpServers": {
    "atlassian-via-proxy": {
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

1. **Client Registration:** On first run, the proxy registers itself as an OAuth client with the upstream server
2. **Authorization:** Opens a browser for user authentication and authorization
3. **Token Exchange:** Exchanges the authorization code for access tokens
4. **Token Storage:** Securely stores tokens in `~/.mcp/auth/`
5. **Auto-Refresh:** Automatically refreshes expired tokens using refresh tokens
6. **Request Proxying:** Adds Bearer token to all proxied requests

**Token Storage Location:**

```
~/.mcp/auth/
├── <server_hash>_tokens.json        # OAuth tokens (access + refresh)
├── <server_hash>_client_info.json   # OAuth client registration
```

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│  MCP Client │◄───────►│  MCP Proxy   │◄───────►│   Upstream   │
│  (Claude)   │   HTTP  │ (This Server)│  OAuth  │  MCP Server  │
└─────────────┘         └──────────────┘         └──────────────┘
                              │
                              │ OAuth Flow
                              ▼
                        ┌──────────────┐
                        │    Browser   │
                        │   (User Auth)│
                        └──────────────┘
```

## Troubleshooting

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

**Solution:** The proxy should auto-refresh. If it fails, clear credentials and re-authenticate:

```bash
python -m custom_server.cli clear
python -m custom_server.main
```

### Connection Refused to Upstream

```
httpx.ConnectError: Connection refused
```

**Solution:** Verify `UPSTREAM_MCP_URL` is correct and the server is accessible.

For more troubleshooting, see [USAGE.md](USAGE.md).
