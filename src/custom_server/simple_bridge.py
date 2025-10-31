"""
Simple HTTP-to-SSE Bridge
Directly forwards Streamable HTTP requests to upstream SSE server without using MCP SDK
"""
import asyncio
import json
import uuid
from typing import Dict, Any
import httpx

from .logger import logger


class SimpleBridge:
    """Simple bridge that forwards requests to upstream SSE server"""
    
    def __init__(self):
        self.sessions: Dict[str, str] = {}  # user_id -> session_id
    
    async def handle_request(
        self, 
        user_id: str, 
        upstream_url: str, 
        access_token: str,
        json_rpc_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a JSON-RPC request by POSTing to upstream /message endpoint"""
        method = json_rpc_request.get("method", "unknown")
        request_id = json_rpc_request.get("id")
        
        try:
            # Get or create session ID for this user
            if user_id not in self.sessions:
                session_id = str(uuid.uuid4())
                self.sessions[user_id] = session_id
                logger.info(f"[SimpleBridge] Created session {session_id} for user {user_id}")
            else:
                session_id = self.sessions[user_id]
            
            logger.debug(f"[SimpleBridge] Forwarding {method} to upstream (session: {session_id})")
            
            # Construct message endpoint URL
            message_url = f"{upstream_url}/message"
            
            # Prepare headers
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Forward the request to upstream
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    message_url,
                    params={"sessionId": session_id},
                    json=json_rpc_request,
                    headers=headers
                )
                
                logger.debug(f"[SimpleBridge] Upstream response status: {response.status_code}")
                
                if response.status_code >= 400:
                    logger.error(f"[SimpleBridge] Upstream error: {response.status_code} - {response.text}")
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Upstream error: {response.text}"
                        }
                    }
                
                # Parse and return response
                response_data = response.json()
                logger.debug(f"[SimpleBridge] Success: {method}")
                return response_data
        
        except httpx.TimeoutException as e:
            logger.error(f"[SimpleBridge] Timeout handling {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Request timeout: {str(e)}"
                }
            }
        except Exception as e:
            logger.error(f"[SimpleBridge] Error handling {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def clear_session(self, user_id: str):
        """Clear session for a user"""
        if user_id in self.sessions:
            del self.sessions[user_id]
            logger.info(f"[SimpleBridge] Cleared session for user {user_id}")


# Global bridge instance
simple_bridge = SimpleBridge()

