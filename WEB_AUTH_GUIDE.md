# Web-Based Authentication Guide

## Overview

The MCP U2M Proxy now features **web-based authentication** where users authenticate through a beautiful web interface instead of automatic terminal-based authentication.

## How It Works

### 1. Start the Server

```bash
export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"
python -m custom_server.main
```

The server starts **without** triggering authentication automatically.

### 2. Visit the Web Interface

Open your browser and go to:

```
http://localhost:8000/
```

You'll see a beautiful web interface showing:

```
🔐 MCP U2M Proxy
User-to-Machine Authentication Proxy for MCP Servers

┌─────────────────────────────────────────┐
│ ❌ Not Authenticated                    │
│ Authentication required to use proxy    │
│                                         │
│ Upstream Server: https://mcp.atlas...  │
└─────────────────────────────────────────┘

[🌐 Authenticate with Upstream Server]
```

### 3. Click Authenticate

When you click the **"Authenticate with Upstream Server"** button:

1. ✅ A popup window opens with the OAuth login page
2. ✅ You log in and authorize the application
3. ✅ The popup redirects back to the proxy
4. ✅ The proxy exchanges the code for tokens
5. ✅ The main page updates to show you're authenticated
6. ✅ MCP endpoints are now available

### 4. Authenticated State

Once authenticated, the interface shows:

```
┌─────────────────────────────────────────┐
│ ✅ Authenticated                        │
│ Your proxy is ready to use              │
│                                         │
│ Upstream Server: https://mcp.atlas...  │
│ Client ID: abc-123-def-456             │
│ Token Expires: Jan 1, 2025 12:00 PM   │
└─────────────────────────────────────────┘

📡 Available Endpoints
SSE: http://localhost:8000/sse
Message: http://localhost:8000/message

[🔄 Refresh Status]
[🗑️ Clear Credentials]
```

### 5. Use the Proxy

Now connect your MCP client to the endpoints shown.

## API Endpoints

The web UI uses these REST APIs:

### Check Authentication Status

```bash
GET /api/auth/status

Response:
{
  "authenticated": true,
  "upstream_url": "https://mcp.atlassian.com/v1",
  "client_id": "abc-123-def-456",
  "expires_at": "2025-01-01T12:00:00"
}
```

### Start Authentication

```bash
POST /api/auth/start

Response:
{
  "success": true,
  "auth_url": "https://mcp.atlassian.com/oauth/authorize?...",
  "message": "Opening browser for authentication..."
}
```

### Clear Credentials

```bash
POST /api/auth/clear

Response:
{
  "success": true,
  "message": "Credentials cleared successfully"
}
```

## Features

### ✨ Beautiful UI

- **Modern Design**: Gradient backgrounds, smooth animations
- **Real-time Status**: Shows current authentication state
- **Token Info**: Displays client ID and expiration
- **Auto-refresh**: Status updates every 30 seconds

### 🔐 Secure Authentication

- **OAuth 2.0 PKCE**: Industry-standard secure flow
- **Popup Window**: Authentication in separate window
- **Auto-detection**: Detects when popup closes
- **Token Storage**: Secure local storage

### 🎯 User-Friendly

- **Clear Messaging**: Always know what's happening
- **One-Click Auth**: Single button to start
- **Status Indicators**: Visual feedback (✅ ❌ ⏳)
- **Error Handling**: Friendly error messages

### 🔄 Management Features

- **Refresh Status**: Check auth state anytime
- **Clear Credentials**: Re-authenticate easily
- **Endpoint Display**: Copy-paste ready endpoints
- **Auto-refresh**: Status updates automatically

## Flow Diagram

```
User → Browser
       ↓
[Visit http://localhost:8000/]
       ↓
[Web UI loads, checks status]
       ↓
[Click "Authenticate" button]
       ↓
[Popup opens with OAuth page]
       ↓
[User logs in & authorizes]
       ↓
[Popup redirects to /oauth/callback]
       ↓
[Proxy exchanges code for tokens]
       ↓
[Tokens saved to ~/.mcp/auth/]
       ↓
[Popup shows success page]
       ↓
[User closes popup]
       ↓
[Main page auto-refreshes status]
       ↓
[✅ Authenticated - Ready to use!]
```

## Code Structure

### Backend (app.py)

```python
# API Endpoints
GET  /                      # Serve web UI
GET  /api/auth/status      # Check auth status
POST /api/auth/start       # Start OAuth flow
POST /api/auth/clear       # Clear credentials
GET  /oauth/callback       # OAuth callback handler

# Proxy Endpoints (require auth)
GET  /sse                  # Server-Sent Events
POST /message              # Message endpoint
ANY  /{path}               # Generic proxy
```

### Frontend (index.html)

```javascript
// Functions
checkStatus()    // Check authentication status
startAuth()      // Start OAuth flow
clearAuth()      // Clear credentials

// UI Updates
showAuthenticated()    // Show authenticated state
showUnauthenticated()  // Show unauthenticated state
showMessage()          // Display messages
```

### OAuth Manager (oauth_manager.py)

```python
# Core OAuth functions
register_client()           # Register with OAuth provider
start_auth_flow()          # Generate auth URL
handle_callback()          # Process OAuth callback
exchange_code_for_tokens() # Exchange code for tokens
get_valid_access_token()   # Get/refresh token
```

## Comparison: Old vs New

### Old Behavior (Automatic)

```
Start Server
    ↓
Auto-detect no auth
    ↓
Automatically open browser
    ↓
Wait in terminal
    ↓
Done
```

**Issues:**
- ❌ No user control
- ❌ Confusing for users
- ❌ Terminal-based
- ❌ Happens on every startup

### New Behavior (Web-Based)

```
Start Server
    ↓
User visits web UI
    ↓
User clicks "Authenticate"
    ↓
Popup opens
    ↓
Done
```

**Benefits:**
- ✅ User-initiated
- ✅ Clear visual feedback
- ✅ Beautiful interface
- ✅ Status persistence

## Troubleshooting

### Popup Blocked

**Issue:** Browser blocks the authentication popup.

**Solution:** 
1. Allow popups for localhost:8000
2. Or manually copy the auth URL from browser console
3. Open in new tab manually

### Status Not Updating

**Issue:** Status doesn't update after authentication.

**Solution:**
1. Click "Refresh Status" button
2. Or reload the page
3. Check browser console for errors

### Authentication Fails

**Issue:** OAuth callback fails.

**Solution:**
1. Check server logs in terminal
2. Verify `UPSTREAM_MCP_URL` is correct
3. Try clearing credentials and re-authenticating

### Connection Refused

**Issue:** Can't connect to upstream server.

**Solution:**
1. Verify upstream URL is accessible
2. Check network connectivity
3. Look for firewall issues

## CLI Still Available

The CLI tools still work for automation:

```bash
# Check status
python -m custom_server.cli status

# Clear credentials
python -m custom_server.cli clear
```

But authentication via CLI is **no longer recommended** - use the web UI instead!

## Example: Complete Workflow

```bash
# Terminal 1: Start the server
$ export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"
$ python -m custom_server.main

Initializing MCP Proxy Server...
Upstream MCP Server: https://mcp.atlassian.com/v1
OAuth Callback Port: 8000
Visit http://localhost:8000/ to authenticate

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

```bash
# Browser: Visit http://localhost:8000/
# 1. See "Not Authenticated" status
# 2. Click "Authenticate with Upstream Server"
# 3. Popup opens → Log in → Authorize
# 4. See "Authentication Successful!" in popup
# 5. Close popup
# 6. Main page now shows "✅ Authenticated"
# 7. Copy endpoint: http://localhost:8000/sse
```

```json
// Terminal 2: Update Claude config
// File: claude_desktop_config.json
{
  "mcpServers": {
    "atlassian": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

```bash
# Terminal 2: Restart Claude Desktop
# Now Claude can use the Atlassian MCP tools!
```

## Summary

The new web-based authentication provides:

✅ **Better UX** - Clear visual interface  
✅ **User Control** - Authenticate when ready  
✅ **Status Visibility** - Always see auth state  
✅ **Easy Management** - Clear/refresh with one click  
✅ **Professional** - Beautiful, modern design  
✅ **Intuitive** - No terminal commands needed  

This is the **recommended way** to use the MCP U2M Proxy!

