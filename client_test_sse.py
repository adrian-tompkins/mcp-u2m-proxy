#!/usr/bin/env python3
"""
Test client using MCP Python SDK
Connects to the proxy's SSE endpoint and lists tools
"""
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    """Test the MCP proxy using the official SDK"""
    print("=" * 60)
    print("MCP SDK Client Test (SSE Transport)")
    print("=" * 60)
    
    # Connect to the proxy's SSE endpoint
    server_url = "http://localhost:8000/sse"
    
    try:
        print(f"\n[Step 1] Connecting to {server_url}...")
        
        # Use the MCP SDK's SSE client
        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                print("[Step 2] Initializing session...")
                init_result = await session.initialize()
                
                print(f"\n✅ Connected to: {init_result.serverInfo.name}")
                print(f"   Version: {init_result.serverInfo.version}")
                print(f"   Protocol: {init_result.protocolVersion}")
                
                # List capabilities
                if init_result.capabilities:
                    print("\n   Server capabilities:")
                    if init_result.capabilities.tools:
                        print(f"   - Tools: ✓")
                    if init_result.capabilities.resources:
                        print(f"   - Resources: ✓")
                    if init_result.capabilities.prompts:
                        print(f"   - Prompts: ✓")
                
                # List tools
                print("\n[Step 3] Listing available tools...")
                tools_result = await session.list_tools()
                
                tools = tools_result.tools
                print(f"\n✅ Found {len(tools)} tools:")
                for i, tool in enumerate(tools, 1):
                    print(f"\n   {i}. {tool.name}")
                    if tool.description:
                        print(f"      Description: {tool.description}")
                    
                    # Show input schema
                    if tool.inputSchema:
                        schema = tool.inputSchema
                        if hasattr(schema, 'properties') and schema.properties:
                            print(f"      Parameters: {', '.join(schema.properties.keys())}")
                        elif isinstance(schema, dict) and 'properties' in schema:
                            print(f"      Parameters: {', '.join(schema['properties'].keys())}")
                
                # Test calling a tool
                if tools:
                    print(f"\n[Step 4] Testing tool call...")
                    first_tool = tools[0]
                    print(f"   Calling: {first_tool.name}")
                    
                    try:
                        # Try calling with empty arguments
                        call_result = await session.call_tool(first_tool.name, {})
                        
                        print(f"\n✅ Tool call successful!")
                        print(f"   Result content items: {len(call_result.content)}")
                        
                        # Display content
                        for idx, item in enumerate(call_result.content[:3], 1):
                            print(f"\n   Content {idx}:")
                            print(f"   Type: {item.type}")
                            if hasattr(item, 'text'):
                                text = item.text[:200] if len(item.text) > 200 else item.text
                                print(f"   Text: {text}...")
                            elif hasattr(item, 'data'):
                                print(f"   Data: {str(item.data)[:200]}...")
                        
                        if call_result.isError:
                            print(f"\n   ⚠️  Tool indicated an error in the result")
                    
                    except Exception as e:
                        print(f"\n   ⚠️  Tool call failed: {e}")
                
                # List resources (if supported)
                if init_result.capabilities and init_result.capabilities.resources:
                    print("\n[Step 5] Listing resources...")
                    try:
                        resources_result = await session.list_resources()
                        resources = resources_result.resources
                        print(f"\n✅ Found {len(resources)} resources:")
                        for i, resource in enumerate(resources[:5], 1):
                            print(f"   {i}. {resource.uri}")
                            if resource.name:
                                print(f"      Name: {resource.name}")
                    except Exception as e:
                        print(f"   ⚠️  Failed to list resources: {e}")
                
                # List prompts (if supported)
                if init_result.capabilities and init_result.capabilities.prompts:
                    print("\n[Step 6] Listing prompts...")
                    try:
                        prompts_result = await session.list_prompts()
                        prompts = prompts_result.prompts
                        print(f"\n✅ Found {len(prompts)} prompts:")
                        for i, prompt in enumerate(prompts[:5], 1):
                            print(f"   {i}. {prompt.name}")
                            if prompt.description:
                                print(f"      {prompt.description}")
                    except Exception as e:
                        print(f"   ⚠️  Failed to list prompts: {e}")
                
                print("\n" + "=" * 60)
                print("✅ Test completed successfully!")
                print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

