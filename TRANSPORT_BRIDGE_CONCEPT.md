# MCP Transport Bridge Concept

## Problem
- **Client**: Only supports Streamable HTTP (POST /mcp)
- **Upstream Server**: Only supports SSE (GET /sse + POST /message)
- **Need**: Proxy to bridge between them

## Architecture

```
┌──────────────┐         ┌─────────────────────────────┐         ┌──────────────┐
│   Client     │         │         Proxy               │         │  Upstream    │
│ (Streamable  │         │   (Protocol Translator)     │         │    (SSE)     │
│    HTTP)     │         │                             │         │              │
└──────────────┘         └─────────────────────────────┘         └──────────────┘
      │                              │                                    │
      │                              │                                    │
      │  1. POST /mcp               │                                    │
      │     (JSON-RPC request)       │                                    │
      │─────────────────────────────>│                                    │
      │                              │  2. Maintain persistent SSE        │
      │                              │     GET /sse                       │
      │                              │<===================================│
      │                              │                                    │
      │                              │  3. Forward request                │
      │                              │     POST /message                  │
      │                              │────────────────────────────────────>│
      │                              │                                    │
      │                              │  4. Response via SSE stream        │
      │                              │<===================================│
      │  5. Stream response          │                                    │
      │<─────────────────────────────│                                    │
      │     (HTTP streaming)         │                                    │
```

## Key Challenges

### 1. Connection Management
- Maintain one persistent SSE connection per user to upstream
- Handle reconnection if SSE connection drops
- Clean up connections when users disconnect

### 2. Request/Response Matching
- Match JSON-RPC request IDs from client to responses from SSE
- Handle multiple concurrent requests from same client
- Timeout requests that don't get responses

### 3. State Management
- Track active SSE connections per user
- Queue requests if connection not established
- Handle session lifecycle

### 4. Error Handling
- What if SSE connection fails mid-request?
- How to communicate upstream SSE errors to HTTP client?
- Handle OAuth token refresh during long-lived connections

## Implementation Options

### Option 1: Use MCP Python SDK (Recommended)

```python
from mcp import ClientSession
from mcp.client.sse import sse_client
import asyncio

class MCPBridge:
    def __init__(self, upstream_url, oauth_manager):
        self.upstream_url = upstream_url
        self.oauth_manager = oauth_manager
        self.sessions = {}  # user_id -> ClientSession
    
    async def get_session(self, user_id: str):
        """Get or create MCP client session for user"""
        if user_id not in self.sessions:
            token = await self.oauth_manager.get_valid_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create SSE client connection
            read, write = await sse_client(
                self.upstream_url,
                headers=headers
            )
            
            # Create MCP session
            session = ClientSession(read, write)
            await session.initialize()
            self.sessions[user_id] = session
        
        return self.sessions[user_id]
    
    async def handle_request(self, user_id: str, json_rpc_request):
        """Handle a JSON-RPC request from client"""
        session = await self.get_session(user_id)
        
        # MCP SDK handles the protocol details
        if json_rpc_request['method'] == 'tools/list':
            result = await session.list_tools()
        elif json_rpc_request['method'] == 'tools/call':
            result = await session.call_tool(
                json_rpc_request['params']['name'],
                json_rpc_request['params'].get('arguments', {})
            )
        # etc...
        
        return result


@app.post("/mcp")
async def streamable_http_endpoint(request: Request):
    """Accept streamable HTTP and bridge to SSE upstream"""
    user_id = get_user_id_from_request(request)
    body = await request.body()
    json_rpc_request = json.loads(body)
    
    bridge = MCPBridge(UPSTREAM_MCP_URL, get_oauth_manager(user_id))
    
    try:
        result = await bridge.handle_request(user_id, json_rpc_request)
        
        # Return as streaming response
        async def stream_result():
            yield json.dumps({
                "jsonrpc": "2.0",
                "id": json_rpc_request['id'],
                "result": result
            })
        
        return StreamingResponse(
            stream_result(),
            media_type="text/event-stream"
        )
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": json_rpc_request['id'],
            "error": {"code": -32603, "message": str(e)}
        })
```

### Option 2: Manual Protocol Translation (Complex)

Build your own SSE connection manager and request/response matcher.
This is significantly more complex and error-prone.

## Recommendation

**Use the MCP Python SDK** (`mcp` package) which already has:
- ✅ SSE client implementation
- ✅ Request/response matching
- ✅ JSON-RPC handling
- ✅ Connection management
- ✅ Error handling

Your proxy would become a **protocol adapter** that:
1. Accepts Streamable HTTP from client
2. Uses MCP SDK to talk to upstream SSE server
3. Translates responses back to Streamable HTTP format

## Alternative: Ask Client to Support SSE

If possible, it might be simpler to configure your client to use SSE instead.
Most MCP clients support both transports.

Check if your Databricks client has a configuration option for transport type:
```python
# Instead of:
transport = "streamable-http"

# Use:
transport = "sse"
```

