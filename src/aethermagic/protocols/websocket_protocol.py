"""
WebSocket Protocol Implementation for AetherMagic
WebSocket-based communication with HTTP REST API fallback for reliability
"""

import asyncio
import json
import random
import time
import aiohttp
from aiohttp import web, WSMsgType
import aiohttp.web_middlewares
from typing import Optional, Callable, Dict, Any, List, Set
import websockets
from urllib.parse import urljoin
import time

from . import ProtocolInterface, ConnectionConfig, AetherMessage, ProtocolType


class WebSocketProtocol(ProtocolInterface):
    """WebSocket + HTTP REST implementation"""
    
    def __init__(self, config: ConnectionConfig, mode: str = 'client'):
        super().__init__(config)
        self.mode = mode  # 'client' or 'server'
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[object] = None
        self.base_url = f"{'https' if config.ssl else 'http'}://{config.host}:{config.port}"
        self.ws_url = f"{'wss' if config.ssl else 'ws'}://{config.host}:{config.port}/ws"
        
        # Server mode components
        self.app: Optional[web.Application] = None
        self.server_runner: Optional[web.AppRunner] = None
        self.websockets: Set = set()
        self.message_storage: Dict[str, List[Dict]] = {}  # topic -> messages
        self.subscriptions: Dict[str, Set] = {}  # topic -> websocket_set
        
    async def connect(self) -> bool:
        """Connect as client or start as server"""
        try:
            if self.mode == 'client':
                return await self._connect_client()
            else:
                return await self._start_server()
        except Exception as e:
            print(f"HTTP/WS: Connection failed - {e}")
            self.connected = False
            return False
    
    async def _connect_client(self) -> bool:
        """Connect as HTTP/WebSocket client"""
        # Create HTTP session
        connector = aiohttp.TCPConnector(
            keepalive_timeout=self.config.keepalive,
            enable_cleanup_closed=True
        )
        
        auth = None
        if self.config.username and self.config.password:
            auth = aiohttp.BasicAuth(self.config.username, self.config.password)
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            auth=auth,
            timeout=timeout
        )
        
        # Test HTTP connection
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status != 200:
                    raise Exception(f"Server returned {response.status}")
        except Exception:
            # Server might not have health endpoint, try WebSocket
            pass
        
        # Connect WebSocket
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                timeout=self.config.timeout,
                ping_interval=self.config.keepalive,
                ping_timeout=self.config.timeout
            )
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
            # Continue without WebSocket for HTTP-only mode
        
        self.connected = True
        return True
    
    async def _start_server(self) -> bool:
        """Start as HTTP/WebSocket server"""
        self.app = web.Application()
        
        # Setup routes
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_post('/publish/{topic:.*}', self._handle_publish)
        self.app.router.add_get('/subscribe/{topic:.*}', self._handle_subscribe)
        self.app.router.add_delete('/subscribe/{topic:.*}', self._handle_unsubscribe)
        self.app.router.add_get('/messages/{topic:.*}', self._handle_get_messages)
        self.app.router.add_get('/ws', self._handle_websocket)
        
        # Setup CORS if needed
        self.app.middlewares.append(self._cors_middleware)
        
        self.server_runner = web.AppRunner(self.app)
        await self.server_runner.setup()
        
        site = web.TCPSite(
            self.server_runner, 
            host=self.config.host,
            port=self.config.port,
            ssl_context=None  # Add SSL context if needed
        )
        
        await site.start()
        
        self.connected = True
        print(f"HTTP/WS Server started on {self.config.host}:{self.config.port}")
        return True
    
    async def disconnect(self) -> bool:
        """Disconnect client or stop server"""
        try:
            if self.mode == 'client':
                if self.websocket:
                    await self.websocket.close()
                if self.session:
                    await self.session.close()
            else:
                # Close all WebSocket connections
                if self.websockets:
                    await asyncio.gather(
                        *[ws.close() for ws in self.websockets],
                        return_exceptions=True
                    )
                if self.server_runner:
                    await self.server_runner.cleanup()
            
            self.connected = False
            return True
        except Exception as e:
            print(f"HTTP/WS: Disconnect failed - {e}")
            return False
    
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish message via HTTP POST and WebSocket"""
        try:
            if not self.connected:
                return False
            
            payload = message.to_json()
            
            if self.mode == 'client':
                # Send via HTTP POST
                if self.session:
                    url = f"{self.base_url}/publish/{topic}"
                    data = {
                        'message': payload,
                        'retain': retain
                    }
                    
                    async with self.session.post(url, json=data) as response:
                        if response.status not in [200, 201]:
                            print(f"HTTP publish failed: {response.status}")
                
                # Send via WebSocket if connected
                if self.websocket:
                    ws_message = {
                        'type': 'publish',
                        'topic': topic,
                        'message': payload,
                        'retain': retain
                    }
                    await self.websocket.send(json.dumps(ws_message))
            
            else:  # server mode
                # Store message if retain=True
                if retain:
                    if topic not in self.message_storage:
                        self.message_storage[topic] = []
                    
                    self.message_storage[topic].append({
                        'message': payload,
                        'timestamp': time.time()
                    })
                    
                    # Keep only last 100 messages per topic
                    if len(self.message_storage[topic]) > 100:
                        self.message_storage[topic] = self.message_storage[topic][-100:]
                
                # Check if this is a load-balanced task (perform action with shared subscription)
                is_load_balanced = (
                    message.action == 'perform' and 
                    topic.startswith('shared:') or
                    topic.startswith('tasks:')
                )
                
                # Broadcast to subscribed WebSocket clients
                if topic in self.subscriptions:
                    ws_message = {
                        'type': 'message',
                        'topic': topic,
                        'message': payload
                    }
                    message_json = json.dumps(ws_message)
                    
                    if is_load_balanced:
                        # Load balanced: send to only one random subscriber
                        clients = list(self.subscriptions[topic])
                        if clients:
                            selected_client = random.choice(clients)
                            try:
                                await selected_client.send_str(message_json)
                            except Exception:
                                # Remove disconnected client
                                self.subscriptions[topic].discard(selected_client)
                    else:
                        # Broadcast to all subscribed clients
                        disconnected = set()
                        for ws in self.subscriptions[topic]:
                            try:
                                await ws.send_str(message_json)
                            except Exception:
                                disconnected.add(ws)
                    
                    # Remove disconnected clients
                    self.subscriptions[topic] -= disconnected
            
            return True
            
        except Exception as e:
            print(f"HTTP/WS: Publish failed - {e}")
            return False
    
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to topic via HTTP or WebSocket"""
        try:
            if not self.connected:
                return False
            
            if self.mode == 'client':
                if self.websocket:
                    # Subscribe via WebSocket
                    ws_message = {
                        'type': 'subscribe',
                        'topic': topic
                    }
                    await self.websocket.send(json.dumps(ws_message))
                    return True
                elif self.session:
                    # HTTP polling mode - just mark as subscribed
                    return True
            
            return True
            
        except Exception as e:
            print(f"HTTP/WS: Subscribe failed - {e}")
            return False
    
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic"""
        try:
            if not self.connected:
                return False
            
            if self.mode == 'client' and self.websocket:
                ws_message = {
                    'type': 'unsubscribe', 
                    'topic': topic
                }
                await self.websocket.send(json.dumps(ws_message))
            
            return True
            
        except Exception as e:
            print(f"HTTP/WS: Unsubscribe failed - {e}")
            return False
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages via WebSocket or HTTP polling"""
        messages = []
        
        if not self.connected:
            return messages
        
        try:
            if self.mode == 'client':
                if self.websocket:
                    # Receive from WebSocket
                    try:
                        message = await asyncio.wait_for(
                            self.websocket.recv(),
                            timeout=0.1
                        )
                        
                        data = json.loads(message)
                        if data['type'] == 'message':
                            messages.append({
                                'topic': data['topic'],
                                'payload': data['message']
                            })
                    except asyncio.TimeoutError:
                        pass
                elif self.session:
                    # HTTP polling mode - check for messages
                    for topic in self.listeners:  # Assuming listeners list exists
                        url = f"{self.base_url}/messages/{topic}"
                        async with self.session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                for msg in data.get('messages', []):
                                    messages.append({
                                        'topic': topic,
                                        'payload': msg['message']
                                    })
        
        except Exception as e:
            print(f"HTTP/WS: Receive failed - {e}")
        
        return messages
    
    # Server-side handlers
    async def _handle_health(self, request):
        """Health check endpoint"""
        return web.json_response({'status': 'ok', 'timestamp': time.time()})
    
    async def _handle_publish(self, request):
        """Handle HTTP publish requests"""
        topic = request.match_info['topic']
        data = await request.json()
        
        message = AetherMessage.from_json(data['message'])
        retain = data.get('retain', False)
        
        success = await self.publish(topic, message, retain)
        
        return web.json_response({
            'success': success,
            'topic': topic
        }, status=200 if success else 500)
    
    async def _handle_subscribe(self, request):
        """Handle HTTP subscribe requests"""
        # This would typically return a long-polling response
        # or establish a Server-Sent Events stream
        return web.json_response({'message': 'Use WebSocket for real-time subscriptions'})
    
    async def _handle_unsubscribe(self, request):
        """Handle HTTP unsubscribe requests"""
        return web.json_response({'success': True})
    
    async def _handle_get_messages(self, request):
        """Get stored messages for a topic"""
        topic = request.match_info['topic']
        messages = self.message_storage.get(topic, [])
        
        return web.json_response({
            'topic': topic,
            'messages': messages
        })
    
    async def _handle_websocket(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        client_subscriptions = set()
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get('type')
                        topic = data.get('topic')
                        
                        if msg_type == 'subscribe' and topic:
                            if topic not in self.subscriptions:
                                self.subscriptions[topic] = set()
                            self.subscriptions[topic].add(ws)
                            client_subscriptions.add(topic)
                            
                        elif msg_type == 'unsubscribe' and topic:
                            if topic in self.subscriptions:
                                self.subscriptions[topic].discard(ws)
                            client_subscriptions.discard(topic)
                            
                        elif msg_type == 'publish' and topic:
                            message = AetherMessage.from_json(data['message'])
                            retain = data.get('retain', False)
                            await self.publish(topic, message, retain)
                            
                    except Exception as e:
                        print(f"WebSocket message error: {e}")
                        
                elif msg.type == WSMsgType.ERROR:
                    print(f"WebSocket error: {ws.exception()}")
                    break
                    
        except Exception as e:
            print(f"WebSocket handler error: {e}")
        finally:
            # Clean up subscriptions
            for topic in client_subscriptions:
                if topic in self.subscriptions:
                    self.subscriptions[topic].discard(ws)
            
            self.websockets.discard(ws)
        
        return ws
    
    @web.middleware
    async def _cors_middleware(self, request, handler):
        """CORS middleware"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response