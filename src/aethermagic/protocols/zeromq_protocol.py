"""
ZeroMQ Protocol Implementation for AetherMagic
High-performance messaging with various patterns (PUB/SUB, PUSH/PULL, REQ/REP)
"""

import asyncio
import json
import zmq
import zmq.asyncio
from typing import Optional, Callable, Dict, Any, List
import threading
import time

from . import ProtocolInterface, ConnectionConfig, AetherMessage, ProtocolType


class ZeroMQProtocol(ProtocolInterface):
    """ZeroMQ implementation with multiple messaging patterns"""
    
    def __init__(self, config: ConnectionConfig, pattern: str = 'pubsub'):
        super().__init__(config)
        self.pattern = pattern  # 'pubsub', 'pushpull', 'reqrep'
        self.context: Optional[zmq.asyncio.Context] = None
        
        # Publisher/Subscriber sockets
        self.publisher: Optional[zmq.asyncio.Socket] = None
        self.subscriber: Optional[zmq.asyncio.Socket] = None
        
        # Push/Pull sockets for load balancing
        self.push_socket: Optional[zmq.asyncio.Socket] = None
        self.pull_socket: Optional[zmq.asyncio.Socket] = None
        
        # Request/Reply sockets
        self.req_socket: Optional[zmq.asyncio.Socket] = None
        self.rep_socket: Optional[zmq.asyncio.Socket] = None
        
        self.subscribed_topics: set = set()
        self.server_mode = config.extra_params.get('server_mode', False)
        
        # ZMQ addresses
        self.pub_address = f"tcp://{config.host}:{config.port}"
        self.sub_address = f"tcp://{config.host}:{config.port}"
        self.push_address = f"tcp://{config.host}:{config.port + 1}"
        self.pull_address = f"tcp://{config.host}:{config.port + 1}"
        self.req_address = f"tcp://{config.host}:{config.port + 2}"
        self.rep_address = f"tcp://{config.host}:{config.port + 2}"
        
    async def connect(self) -> bool:
        """Initialize ZeroMQ context and sockets"""
        try:
            self.context = zmq.asyncio.Context()
            
            if self.pattern in ['pubsub', 'all']:
                await self._setup_pubsub()
            
            if self.pattern in ['pushpull', 'all']:
                await self._setup_pushpull()
                
            if self.pattern in ['reqrep', 'all']:
                await self._setup_reqrep()
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"ZeroMQ: Connection failed - {e}")
            self.connected = False
            return False
    
    async def _setup_pubsub(self):
        """Setup Publisher/Subscriber pattern"""
        if self.server_mode:
            # Server: Bind publisher socket
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.bind(self.pub_address)
            
            # Also create subscriber for receiving from clients
            self.subscriber = self.context.socket(zmq.SUB)
            # Bind to different port for client publishers
            client_pub_port = self.config.port + 10
            client_pub_address = f"tcp://*:{client_pub_port}"
            self.subscriber.bind(client_pub_address)
            
        else:
            # Client: Connect to server's publisher
            self.subscriber = self.context.socket(zmq.SUB)
            self.subscriber.connect(self.sub_address)
            
            # Connect publisher to server's subscriber port
            self.publisher = self.context.socket(zmq.PUB)
            server_sub_port = self.config.port + 10
            server_sub_address = f"tcp://{self.config.host}:{server_sub_port}"
            self.publisher.connect(server_sub_address)
    
    async def _setup_pushpull(self):
        """Setup Push/Pull pattern for load balancing"""
        if self.server_mode:
            # Server: Bind pull socket to receive tasks
            self.pull_socket = self.context.socket(zmq.PULL)
            self.pull_socket.bind(self.pull_address)
            
            # Bind push socket to distribute tasks
            self.push_socket = self.context.socket(zmq.PUSH)
            task_dist_port = self.config.port + 11
            task_dist_address = f"tcp://*:{task_dist_port}"
            self.push_socket.bind(task_dist_address)
            
        else:
            # Client: Connect push socket to send tasks
            self.push_socket = self.context.socket(zmq.PUSH)
            self.push_socket.connect(self.push_address)
            
            # Connect pull socket to receive tasks
            self.pull_socket = self.context.socket(zmq.PULL)
            task_dist_port = self.config.port + 11
            task_dist_address = f"tcp://{self.config.host}:{task_dist_port}"
            self.pull_socket.connect(task_dist_address)
    
    async def _setup_reqrep(self):
        """Setup Request/Reply pattern"""
        if self.server_mode:
            # Server: Bind reply socket
            self.rep_socket = self.context.socket(zmq.REP)
            self.rep_socket.bind(self.rep_address)
        else:
            # Client: Connect request socket
            self.req_socket = self.context.socket(zmq.REQ)
            self.req_socket.connect(self.req_address)
    
    async def disconnect(self) -> bool:
        """Close all sockets and terminate context"""
        try:
            sockets = [
                self.publisher, self.subscriber,
                self.push_socket, self.pull_socket, 
                self.req_socket, self.rep_socket
            ]
            
            for socket in sockets:
                if socket:
                    socket.close()
            
            if self.context:
                self.context.term()
            
            self.connected = False
            return True
            
        except Exception as e:
            print(f"ZeroMQ: Disconnect failed - {e}")
            return False
    
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish message using appropriate pattern"""
        try:
            if not self.connected:
                return False
            
            # Prepare message
            msg_data = {
                'topic': topic,
                'message': message.to_json(),
                'timestamp': time.time(),
                'retain': retain
            }
            
            serialized = json.dumps(msg_data).encode('utf-8')
            
            # Determine which socket to use based on message type
            if message.action == 'perform':
                # Use push/pull for load-balanced task distribution
                if self.push_socket:
                    await self.push_socket.send_multipart([
                        topic.encode('utf-8'),
                        serialized
                    ])
            else:
                # Use pub/sub for status updates and notifications
                if self.publisher:
                    await self.publisher.send_multipart([
                        topic.encode('utf-8'),
                        serialized
                    ])
            
            return True
            
        except Exception as e:
            print(f"ZeroMQ: Publish failed - {e}")
            return False
    
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to topic"""
        try:
            if not self.connected:
                return False
            
            # Subscribe on subscriber socket
            if self.subscriber:
                self.subscriber.setsockopt(zmq.SUBSCRIBE, topic.encode('utf-8'))
                self.subscribed_topics.add(topic)
            
            return True
            
        except Exception as e:
            print(f"ZeroMQ: Subscribe failed - {e}")
            return False
    
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic"""
        try:
            if not self.connected:
                return False
            
            if self.subscriber and topic in self.subscribed_topics:
                self.subscriber.setsockopt(zmq.UNSUBSCRIBE, topic.encode('utf-8'))
                self.subscribed_topics.remove(topic)
            
            return True
            
        except Exception as e:
            print(f"ZeroMQ: Unsubscribe failed - {e}")
            return False
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages from all applicable sockets"""
        messages = []
        
        if not self.connected:
            return messages
        
        try:
            # Check subscriber socket (pub/sub messages)
            if self.subscriber:
                try:
                    topic, data = await asyncio.wait_for(
                        self.subscriber.recv_multipart(zmq.NOBLOCK),
                        timeout=0.01
                    )
                    
                    msg_data = json.loads(data.decode('utf-8'))
                    messages.append({
                        'topic': topic.decode('utf-8'),
                        'payload': msg_data['message']
                    })
                except (zmq.Again, asyncio.TimeoutError):
                    pass
            
            # Check pull socket (task messages)
            if self.pull_socket:
                try:
                    topic, data = await asyncio.wait_for(
                        self.pull_socket.recv_multipart(zmq.NOBLOCK),
                        timeout=0.01
                    )
                    
                    msg_data = json.loads(data.decode('utf-8'))
                    messages.append({
                        'topic': topic.decode('utf-8'),
                        'payload': msg_data['message']
                    })
                except (zmq.Again, asyncio.TimeoutError):
                    pass
            
            # Check reply socket (if server mode)
            if self.rep_socket and self.server_mode:
                try:
                    request = await asyncio.wait_for(
                        self.rep_socket.recv_string(zmq.NOBLOCK),
                        timeout=0.01
                    )
                    
                    # Process request and send reply
                    req_data = json.loads(request)
                    
                    # Echo back for now, can be customized
                    reply = {
                        'status': 'received',
                        'timestamp': time.time(),
                        'original': req_data
                    }
                    
                    await self.rep_socket.send_string(json.dumps(reply))
                    
                except (zmq.Again, asyncio.TimeoutError):
                    pass
            
        except Exception as e:
            print(f"ZeroMQ: Receive failed - {e}")
        
        return messages
    
    async def send_request(self, topic: str, message: AetherMessage) -> Optional[Dict[str, Any]]:
        """Send request and wait for reply (REQ/REP pattern)"""
        if not self.req_socket or not self.connected:
            return None
        
        try:
            request = {
                'topic': topic,
                'message': message.to_json(),
                'timestamp': time.time()
            }
            
            await self.req_socket.send_string(json.dumps(request))
            
            # Wait for reply
            reply = await asyncio.wait_for(
                self.req_socket.recv_string(),
                timeout=self.config.timeout
            )
            
            return json.loads(reply)
            
        except Exception as e:
            print(f"ZeroMQ: Request failed - {e}")
            return None
    
    def generate_topic(self, job: str, task: str, context: str, tid: str, action: str, shared: bool = False, workgroup: str = "") -> str:
        """Generate ZeroMQ topic"""
        if shared:
            # For shared/load-balanced topics, use workgroup in the topic
            group = workgroup or "default"
            return f"shared.{self.config.union}.{job}.{group}.{task}.{action}"
        else:
            return f"{self.config.union}.{job}.{task}.{context}.{tid}.{action}"


class ZeroMQBroker:
    """ZeroMQ Broker for message routing and load balancing"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.context = zmq.asyncio.Context()
        self.running = False
        
        # Sockets for different patterns
        self.frontend_sub = None  # Receives from publishers
        self.backend_pub = None   # Sends to subscribers
        self.task_receiver = None # Receives tasks
        self.task_sender = None   # Distributes tasks to workers
        
    async def start(self):
        """Start the broker"""
        try:
            # Frontend for receiving published messages
            self.frontend_sub = self.context.socket(zmq.SUB)
            self.frontend_sub.bind(f"tcp://*:{self.config.port}")
            self.frontend_sub.setsockopt(zmq.SUBSCRIBE, b"")  # Subscribe to all
            
            # Backend for sending to subscribers
            self.backend_pub = self.context.socket(zmq.PUB)
            self.backend_pub.bind(f"tcp://*:{self.config.port + 1}")
            
            # Task distribution sockets
            self.task_receiver = self.context.socket(zmq.PULL)
            self.task_receiver.bind(f"tcp://*:{self.config.port + 2}")
            
            self.task_sender = self.context.socket(zmq.PUSH)
            self.task_sender.bind(f"tcp://*:{self.config.port + 3}")
            
            self.running = True
            
            # Start broker loops
            asyncio.create_task(self._message_broker_loop())
            asyncio.create_task(self._task_broker_loop())
            
            print(f"ZeroMQ Broker started on ports {self.config.port}-{self.config.port + 3}")
            return True
            
        except Exception as e:
            print(f"ZeroMQ Broker: Start failed - {e}")
            return False
    
    async def _message_broker_loop(self):
        """Broker loop for pub/sub messages"""
        while self.running:
            try:
                # Receive from frontend and forward to backend
                message = await self.frontend_sub.recv_multipart(zmq.NOBLOCK)
                await self.backend_pub.send_multipart(message)
            except zmq.Again:
                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"Message broker error: {e}")
    
    async def _task_broker_loop(self):
        """Broker loop for task distribution"""
        while self.running:
            try:
                # Receive tasks and distribute to workers
                task = await self.task_receiver.recv_multipart(zmq.NOBLOCK)
                await self.task_sender.send_multipart(task)
            except zmq.Again:
                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"Task broker error: {e}")
    
    async def stop(self):
        """Stop the broker"""
        self.running = False
        
        sockets = [
            self.frontend_sub, self.backend_pub,
            self.task_receiver, self.task_sender
        ]
        
        for socket in sockets:
            if socket:
                socket.close()
        
        self.context.term()