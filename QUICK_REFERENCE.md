# MCP U2M Proxy - Quick Reference Card

## 🚀 Quick Start

```bash
# 1. Set upstream server
export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"

# 2. Start proxy
python -m custom_server.main

# 3. Open browser and visit:
# http://localhost:8000/

# 4. Click "Authenticate" button in the web UI

# 5. Connect Claude Desktop to:
# http://localhost:8000/sse
```

## 📋 Common Commands

| Command | Description |
|---------|-------------|
| `python -m custom_server.main` | Start proxy server |
| `python -m custom_server.cli status` | Check auth status |
| `python -m custom_server.cli clear` | Clear credentials |
| `python test_proxy.py` | Test proxy |
| `uvicorn custom_server.app:app --reload` | Dev mode |

## 🔐 Authentication Files

```
~/.mcp/auth/
├── <hash>_tokens.json        # Your access tokens
└── <hash>_client_info.json   # OAuth client info
```

## 🌐 Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Homepage |
| `GET /sse` | Server-Sent Events (authenticated) |
| `POST /message` | Messages (authenticated) |
| `GET /oauth/callback` | OAuth callback (internal) |

## ⚙️ Environment Variables

```bash
export UPSTREAM_MCP_URL="https://mcp.atlassian.com/v1"  # Required
export OAUTH_CALLBACK_PORT="8000"                       # Optional
```

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Browser won't open | Copy URL from terminal |
| 401 errors | `python -m custom_server.cli clear` then restart |
| Connection refused | Check UPSTREAM_MCP_URL |
| Timeout | Complete auth within 5 minutes |

## 📝 Claude Desktop Config

```json
{
  "mcpServers": {
    "atlassian": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

## 🔄 Re-authenticate

```bash
python -m custom_server.cli clear
python -m custom_server.main
```

## 📚 Documentation

- **README.md** - Overview and setup
- **USAGE.md** - Detailed usage guide
- **IMPLEMENTATION_SUMMARY.md** - Technical details

## 🆘 Need Help?

```bash
python -m custom_server.cli help
```

## ✅ Verify Setup

```bash
# Check auth status
python -m custom_server.cli status

# Test connection
python test_proxy.py

# Check logs
ls -la ~/.mcp/auth/
```

