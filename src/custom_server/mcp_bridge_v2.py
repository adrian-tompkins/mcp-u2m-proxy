"""
MCP Protocol Bridge V2
Properly uses MCP SDK with async context managers
"""
import asyncio
import json
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client

from .logger import logger


class MCPBridgeV2:
    """Manages MCP client connections to upstream SSE servers"""
    
    def __init__(self):
        # We don't cache sessions - each request creates a new one
        # This avoids the complexity of managing long-lived sessions
        pass
    
    async def handle_request(
        self, 
        user_id: str, 
        upstream_url: str, 
        access_token: str,
        json_rpc_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a JSON-RPC request by creating a temporary MCP session"""
        method = json_rpc_request.get("method", "unknown")
        request_id = json_rpc_request.get("id")
        
        try:
            logger.debug(f"[BridgeV2] Handling {method} for user {user_id}")
            
            # Construct SSE endpoint URL
            if upstream_url.endswith("/sse"):
                sse_endpoint = upstream_url
            else:
                sse_endpoint = f"{upstream_url}/sse"
            
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            logger.debug(f"[BridgeV2] Connecting to {sse_endpoint}")
            
            # Use proper async context managers
            async with sse_client(sse_endpoint, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    logger.debug(f"[BridgeV2] Session established, calling {method}")
                    
                    # Route to appropriate MCP method
                    params = json_rpc_request.get("params", {})
                    
                    if method == "initialize":
                        result = await asyncio.wait_for(session.initialize(), timeout=30.0)
                        response_data = {
                            "protocolVersion": result.protocolVersion,
                            "capabilities": result.capabilities.model_dump() if result.capabilities else {},
                            "serverInfo": result.serverInfo.model_dump()
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
                        logger.warning(f"[BridgeV2] Unsupported method: {method}")
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        }
                    
                    logger.debug(f"[BridgeV2] Success: {method}")
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": response_data
                    }
                    logger.debug(f"[BridgeV2] Returning response: {json.dumps(response)[:200]}")
                    return response
        
        except asyncio.TimeoutError as e:
            logger.error(f"[BridgeV2] Timeout handling {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Request timeout"
                }
            }
        except Exception as e:
            logger.error(f"[BridgeV2] Error handling {method}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }


# Global bridge instance
mcp_bridge_v2 = MCPBridgeV2()

