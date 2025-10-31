#!/usr/bin/env python3
"""
Test client for MCP Streamable HTTP endpoint
Connects to /mcp endpoint and lists tools
"""
import asyncio
import json
import httpx


class StreamableHTTPClient:
    """Simple MCP client using Streamable HTTP transport"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.request_id = 0
    
    def _next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def _send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params:
            request["params"] = params
        
        print(f"\n→ Sending {method}...")
        print(f"  Request: {json.dumps(request, indent=2)}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.base_url,
                json=request,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"← Received response")
            print(f"  Response: {json.dumps(result, indent=2)}")
            
            return result
    
    async def initialize(self) -> dict:
        """Initialize the MCP session"""
        return await self._send_request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "streamable-http-test-client",
                    "version": "1.0.0"
                }
            }
        )
    
    async def list_tools(self) -> dict:
        """List available tools"""
        return await self._send_request("tools/list")
    
    async def call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """Call a tool"""
        return await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments or {}
            }
        )


async def main():
    """Test the MCP Streamable HTTP client"""
    print("=" * 60)
    print("MCP Streamable HTTP Client Test")
    print("=" * 60)
    
    # Connect to the proxy's /mcp endpoint
    client = StreamableHTTPClient("http://localhost:8000/mcp")
    
    try:
        # Step 1: Initialize
        print("\n[Step 1] Initializing connection...")
        init_result = await client.initialize()
        
        if "error" in init_result:
            print(f"\n❌ Initialization failed: {init_result['error']}")
            return
        
        server_info = init_result.get("result", {}).get("serverInfo", {})
        print(f"\n✅ Connected to: {server_info.get('name', 'Unknown')}")
        print(f"   Version: {server_info.get('version', 'Unknown')}")
        
        # Step 2: List tools
        print("\n[Step 2] Listing available tools...")
        tools_result = await client.list_tools()
        
        if "error" in tools_result:
            print(f"\n❌ Failed to list tools: {tools_result['error']}")
            return
        
        tools = tools_result.get("result", {}).get("tools", [])
        print(f"\n✅ Found {len(tools)} tools:")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.get('name')}")
            if tool.get('description'):
                print(f"      {tool.get('description')}")
        
        # Step 3: Call a tool (if available)
        if tools:
            print("\n[Step 3] Testing tool call...")
            first_tool = tools[0]
            tool_name = first_tool.get("name")
            print(f"   Calling: {tool_name}")
            
            try:
                # Call with empty arguments (or adapt based on the tool)
                call_result = await client.call_tool(tool_name, {})
                
                if "error" in call_result:
                    print(f"\n⚠️  Tool call returned error: {call_result['error']}")
                else:
                    print(f"\n✅ Tool call successful!")
                    content = call_result.get("result", {}).get("content", [])
                    if content:
                        print(f"   Response content:")
                        for item in content[:3]:  # Show first 3 items
                            print(f"   - {item}")
            except Exception as e:
                print(f"\n⚠️  Tool call failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
    
    except httpx.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

