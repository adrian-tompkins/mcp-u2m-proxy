"""
MCP Protocol Bridge
Translates between Streamable HTTP (client) and SSE (upstream server)
"""
import asyncio
import json
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession, types
from mcp.client.sse import sse_client

from .logger import logger


class MCPBridge:
    """Manages MCP client sessions to upstream SSE servers"""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.session_locks: Dict[str, asyncio.Lock] = {}
        self.session_contexts: Dict[str, Any] = {}  # Keep SSE contexts alive
    
    async def get_session(self, user_id: str, upstream_url: str, access_token: str) -> ClientSession:
        """Get or create an MCP client session for a user"""
        if user_id not in self.session_locks:
            self.session_locks[user_id] = asyncio.Lock()
        
        async with self.session_locks[user_id]:
            # Check if we have a valid session
            if user_id in self.sessions:
                # TODO: Check if session is still alive
                return self.sessions[user_id]
            
            # Create new session
            logger.info(f"Creating new MCP session for user: {user_id}")
            
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            # Construct SSE endpoint URL (handle if /sse already in URL)
            if upstream_url.endswith("/sse"):
                sse_endpoint = upstream_url
            else:
                sse_endpoint = f"{upstream_url}/sse"
            logger.debug(f"[Bridge] Connecting to SSE endpoint: {sse_endpoint}")
            logger.debug(f"[Bridge] Auth header: Bearer {access_token[:20]}...")
            
            # Connect via SSE - manually enter context to keep it alive
            try:
                logger.debug("[Bridge] Creating SSE context...")
                sse_context = sse_client(sse_endpoint, headers=headers)
                
                logger.debug("[Bridge] Entering SSE context (this may take a moment)...")
                read, write = await asyncio.wait_for(
                    sse_context.__aenter__(),
                    timeout=10.0
                )
                logger.debug("[Bridge] SSE context entered successfully")
                
                # Create MCP session
                logger.debug("[Bridge] Creating ClientSession...")
                session = ClientSession(read, write)
                logger.info(f"[Bridge] MCP session created for user {user_id} (not yet initialized)")
            except asyncio.TimeoutError as e:
                logger.error(f"[Bridge] Timeout while establishing connection or initializing: {e}")
                raise Exception("Timeout connecting to upstream SSE server") from e
            except Exception as e:
                logger.error(f"[Bridge] Error establishing connection: {e}")
                raise
            
            # Store both session and context to keep connection alive
            self.sessions[user_id] = session
            self.session_contexts[user_id] = sse_context
            
            return session
    
    async def close_session(self, user_id: str):
        """Close a user's MCP session"""
        if user_id in self.sessions:
            try:
                # Close the SSE context manager to clean up connection
                if user_id in self.session_contexts:
                    await self.session_contexts[user_id].__aexit__(None, None, None)
                    del self.session_contexts[user_id]
                
                del self.sessions[user_id]
                logger.info(f"Closed MCP session for user: {user_id}")
            except Exception as e:
                logger.error(f"Error closing session for user {user_id}: {e}")
    
    async def handle_request(
        self, 
        user_id: str, 
        upstream_url: str, 
        access_token: str,
        json_rpc_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a JSON-RPC request by forwarding to upstream via MCP session"""
        # Extract method early for error handling
        method = json_rpc_request.get("method", "unknown")
        request_id = json_rpc_request.get("id")
        
        try:
            session = await self.get_session(user_id, upstream_url, access_token)
            
            params = json_rpc_request.get("params", {})
            
            logger.debug(f"[Bridge] Handling {method} for user {user_id}")
            
            # Route to appropriate MCP method (with timeout)
            if method == "initialize":
                logger.debug(f"[Bridge] Calling session.initialize()...")
                result = await asyncio.wait_for(session.initialize(), timeout=30.0)
                logger.debug(f"[Bridge] Initialize complete")
                response_data = {
                    "protocolVersion": result.protocol_version,
                    "capabilities": result.capabilities.model_dump() if result.capabilities else {},
                    "serverInfo": result.server_info.model_dump()
                }
            
            elif method == "tools/list":
                result = await asyncio.wait_for(session.list_tools(), timeout=30.0)
                response_data = {
                    "tools": [tool.model_dump() for tool in result.tools]
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await asyncio.wait_for(session.call_tool(tool_name, arguments), timeout=60.0)
                response_data = {
                    "content": [item.model_dump() for item in result.content],
                    "isError": result.isError if hasattr(result, "isError") else False
                }
            
            elif method == "resources/list":
                result = await asyncio.wait_for(session.list_resources(), timeout=30.0)
                response_data = {
                    "resources": [resource.model_dump() for resource in result.resources]
                }
            
            elif method == "resources/read":
                uri = params.get("uri")
                result = await asyncio.wait_for(session.read_resource(uri), timeout=30.0)
                response_data = {
                    "contents": [content.model_dump() for content in result.contents]
                }
            
            elif method == "prompts/list":
                result = await asyncio.wait_for(session.list_prompts(), timeout=30.0)
                response_data = {
                    "prompts": [prompt.model_dump() for prompt in result.prompts]
                }
            
            elif method == "prompts/get":
                prompt_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await asyncio.wait_for(session.get_prompt(prompt_name, arguments), timeout=30.0)
                response_data = {
                    "messages": [msg.model_dump() for msg in result.messages]
                }
            
            else:
                logger.warning(f"[Bridge] Unsupported method: {method}")
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            # Success response
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": response_data
            }
        
        except Exception as e:
            logger.error(f"[Bridge] Error handling {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": json_rpc_request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }


# Global bridge instance
mcp_bridge = MCPBridge()

