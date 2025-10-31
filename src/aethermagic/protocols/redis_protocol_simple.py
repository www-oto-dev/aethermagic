"""
Simplified Redis Protocol Implementation for AetherMagic
Uses only Redis Pub/Sub but with separate connections for publishing and subscribing
"""

import asyncio
import json
from typing import Optional, Callable, Dict, Any, List
import redis.asyncio as redis
from redis.asyncio.client import PubSub

from . import ProtocolInterface, ConnectionConfig, AetherMessage, ProtocolType


class RedisProtocol(ProtocolInterface):
    """Simple Redis PubSub with separate publish/subscribe connections"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.publish_client: Optional[redis.Redis] = None
        self.subscribe_client: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.subscribed_channels: set = set()
        
    async def connect(self) -> bool:
        """Connect to Redis server"""
        try:
            # Create Redis connection parameters
            connection_params = {
                'host': self.config.host,
                'port': self.config.port,
                'decode_responses': True,
                'socket_timeout': self.config.timeout,
                'socket_keepalive': True,
                'socket_keepalive_options': {}
            }
            
            # Add SSL if needed
            if self.config.ssl:
                connection_params['ssl'] = True
                connection_params['ssl_cert_reqs'] = None
            
            # Add auth if provided
            if self.config.username and self.config.password:
                connection_params['username'] = self.config.username
                connection_params['password'] = self.config.password
            elif self.config.password:
                connection_params['password'] = self.config.password
                
            # Add extra parameters
            connection_params.update(self.config.extra_params)
            
            # Create separate clients for publishing and subscribing
            self.publish_client = redis.Redis(**connection_params)
            self.subscribe_client = redis.Redis(**connection_params)
            
            # Test connections (ping is synchronous in this version)
            try:
                self.publish_client.ping()
                self.subscribe_client.ping()
            except:
                # Try async version
                await self.publish_client.ping()
                await self.subscribe_client.ping()
            
            # Create pub/sub connection
            self.pubsub = self.subscribe_client.pubsub()
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Redis: Connection failed - {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Redis"""
        try:
            if self.pubsub:
                await self.pubsub.close()
            if self.subscribe_client:
                await self.subscribe_client.close()
            if self.publish_client:
                await self.publish_client.close()
            self.connected = False
            return True
        except Exception as e:
            print(f"Redis: Disconnect failed - {e}")
            return False
    
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish message to Redis channel"""
        try:
            if not self.publish_client or not self.connected:
                return False
                
            # Use pub/sub for all messages
            try:
                # Try sync version first
                self.publish_client.publish(topic, message.to_json())
            except:
                # Try async version
                await self.publish_client.publish(topic, message.to_json())
            
            return True
            
        except Exception as e:
            print(f"Redis: Publish failed - {e}")
            return False
    
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to Redis channel"""
        try:
            if not self.pubsub or not self.connected:
                return False
                
            # Handle wildcard patterns
            if '*' in topic or '?' in topic or '[' in topic:
                await self.pubsub.psubscribe(topic)
            else:
                await self.pubsub.subscribe(topic)
                
            self.subscribed_channels.add(topic)
            return True
            
        except Exception as e:
            print(f"Redis: Subscribe failed - {e}")
            return False
    
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from Redis channel"""
        try:
            if not self.pubsub or not self.connected:
                return False
                
            if '*' in topic or '?' in topic or '[' in topic:
                await self.pubsub.punsubscribe(topic)
            else:
                await self.pubsub.unsubscribe(topic)
                
            self.subscribed_channels.discard(topic)
            return True
            
        except Exception as e:
            print(f"Redis: Unsubscribe failed - {e}")
            return False
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages from subscribed channels"""
        messages = []
        
        if not self.pubsub or not self.connected:
            return messages
            
        # Don't try to read if no subscriptions
        if not self.subscribed_channels:
            return messages
            
        try:
            # Get message with timeout to avoid blocking
            message = await asyncio.wait_for(
                self.pubsub.get_message(ignore_subscribe_messages=True),
                timeout=0.1
            )
            
            if message and message['type'] in ['message', 'pmessage']:
                channel = message['channel']
                data = message['data']
                
                if data:
                    messages.append({
                        'topic': channel,
                        'payload': data
                    })
                    
        except asyncio.TimeoutError:
            pass  # No messages available
        except Exception as e:
            print(f"Redis: Receive failed - {e}")
            
        return messages
    
    def generate_topic(self, job: str, task: str, context: str, tid: str, action: str, shared: bool = False, workgroup: str = "") -> str:
        """Generate Redis channel name - use same format as MQTT for simplicity"""
        return f"{self.config.union}:{job}:{task}:{context}:{tid}:{action}"