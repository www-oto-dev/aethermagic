"""
Redis Protocol Implementation for AetherMagic
Uses Redis Pub/Sub for messaging with Redis Lists for task distribution
"""

import asyncio
import json
import time
from typing import Optional, Callable, Dict, Any, List
import redis.asyncio as redis
from redis.asyncio.client import PubSub

from . import ProtocolInterface, ConnectionConfig, AetherMessage, ProtocolType


class RedisProtocol(ProtocolInterface):
    """Redis implementation using Lists for 'perform' tasks and PubSub for other messages"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.client: Optional[redis.Redis] = None
        self.pubsub: Optional[PubSub] = None
        self.subscribed_channels: set = set()
        self.task_queues: Dict[str, bool] = {}  # Track task queues we're listening to
        
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
            
            # Create Redis client
            self.client = redis.Redis(**connection_params)
            
            # Test connection
            self.client.ping()
            
            # Create pub/sub connection
            self.pubsub = self.client.pubsub()
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Redis: Connection failed - {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Redis"""
        try:
            # Stop all task queue consumers
            self.task_queues.clear()
            
            if self.pubsub:
                await self.pubsub.close()
            if self.client:
                await self.client.close()
            self.connected = False
            return True
        except Exception as e:
            print(f"Redis: Disconnect failed - {e}")
            return False
    
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish message - use Lists for 'perform' actions, PubSub for others"""
        try:
            if not self.client or not self.connected:
                return False
            
            # For 'perform' actions, use Redis Lists for task distribution
            if message.action == 'perform':
                # Push task to Redis List (FIFO queue)
                task_data = {
                    'topic': topic,
                    'message': message.to_json(),
                    'timestamp': time.time()
                }
                
                # Use lpush (add to left) and consumers use brpop (pop from right) for FIFO
                await self.client.lpush(topic, json.dumps(task_data))
                return True
            else:
                # For other actions (status, complete, idle, online), use pub/sub  
                await self.client.publish(topic, message.to_json())
                return True
            
        except Exception as e:
            print(f"Redis: Publish failed - {e}")
            return False
    
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to Redis - use List consumer for 'perform' actions, PubSub for others"""
        try:
            if not self.connected:
                return False
            
            # Check if this is a 'perform' action topic
            if topic.endswith(':perform'):
                # Start List consumer for task distribution
                if topic not in self.task_queues:
                    self.task_queues[topic] = True
                    # Start background consumer task
                    asyncio.create_task(self._consume_from_list(topic, callback))
                return True
            else:
                # Use regular PubSub for other actions
                if not self.pubsub:
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
    
    async def _consume_from_list(self, topic: str, callback: Optional[Callable]):
        """Background consumer for Redis List (for 'perform' actions)"""
        print(f"Redis: Started List consumer for {topic} (channel: {self.config.channel})")
        
        while self.connected and topic in self.task_queues:
            try:
                # Non-blocking check for tasks in Redis List
                if self.client:
                    result = await self.client.brpop([topic], timeout=1)
                    
                    if result:
                        queue_name, task_json = result
                        task_data = json.loads(task_json)
                        
                        # Parse message and call callback
                        if callback:
                            message = AetherMessage.from_json(task_data['message'])
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(message)
                                else:
                                    callback(message)
                            except Exception as e:
                                print(f"Redis: Task callback failed - {e}")
                
            except Exception as e:
                if "timeout" not in str(e).lower():
                    print(f"Redis: List consumer error - {e}")
                await asyncio.sleep(0.1)
        
        print(f"Redis: Stopped List consumer for {topic} (channel: {self.config.channel})")

    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages from PubSub channels (List messages handled by _consume_from_list)"""
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
        # For now, use simple pub/sub format like MQTT
        return f"{self.config.union}:{job}:{task}:{context}:{tid}:{action}"
    
    async def _push_task_to_queue(self, topic: str, message: AetherMessage) -> bool:
        """Push task to Redis list for load balancing"""
        try:
            if not self.client or not self.connected:
                return False
            
            # Push task to list (FIFO queue)
            task_data = {
                'topic': topic,
                'message': message.to_json(),
                'timestamp': time.time()
            }
            
            await self.client.lpush(topic, json.dumps(task_data))
            return True
            
        except Exception as e:
            print(f"Redis: Task queue push failed - {e}")
            return False
    
    async def _pop_task_from_queue(self, topic: str) -> Optional[Dict[str, Any]]:
        """Pop task from Redis list (blocking)"""
        try:
            if not self.client or not self.connected:
                return None
            
            # Blocking pop from list with timeout
            result = await self.client.brpop(topic, timeout=1)
            if result:
                queue_name, task_json = result
                task_data = json.loads(task_json)
                return task_data
            
            return None
            
        except Exception as e:
            print(f"Redis: Task queue pop failed - {e}")
            return None


class RedisStreamProtocol(RedisProtocol):
    """Redis Streams implementation with consumer groups for load balancing"""
    
    def __init__(self, config: ConnectionConfig, consumer_group: str = "workers", consumer_name: str = None):
        super().__init__(config)
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name or f"worker_{id(self)}"
        self.streams: Dict[str, str] = {}  # stream -> last_id mapping
        
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish message to Redis Stream"""
        try:
            if not self.client or not self.connected:
                return False
                
            stream_key = f"stream:{topic}"
            
            # Add message to stream
            await self.client.xadd(stream_key, message.to_dict())
            
            # Also publish to pub/sub for immediate notifications
            await super().publish(topic, message, retain=False)
            
            return True
            
        except Exception as e:
            print(f"Redis Stream: Publish failed - {e}")
            return False
    
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to Redis Stream with consumer group"""
        try:
            if not self.client or not self.connected:
                return False
                
            stream_key = f"stream:{topic}"
            
            # Create consumer group if it doesn't exist
            try:
                await self.client.xgroup_create(stream_key, self.consumer_group, id='0', mkstream=True)
            except Exception:
                pass  # Group might already exist
            
            # Track this stream
            self.streams[stream_key] = '>'
            
            # Also subscribe to pub/sub for immediate notifications  
            await super().subscribe(topic, callback)
            
            return True
            
        except Exception as e:
            print(f"Redis Stream: Subscribe failed - {e}")
            return False
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages from Redis Streams and Pub/Sub"""
        messages = []
        
        if not self.client or not self.connected:
            return messages
            
        try:
            # First check pub/sub for immediate messages
            pubsub_messages = await super().receive_messages()
            messages.extend(pubsub_messages)
            
            # Then check streams for reliable delivery
            if self.streams:
                stream_messages = await self.client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    self.streams,
                    count=10,
                    block=100  # 100ms timeout
                )
                
                for stream_key, stream_msgs in stream_messages:
                    topic = stream_key.replace('stream:', '')
                    
                    for msg_id, fields in stream_msgs:
                        # Convert Redis hash to AetherMessage format
                        aether_msg = AetherMessage.from_dict(fields)
                        
                        messages.append({
                            'topic': topic,
                            'payload': aether_msg.to_json(),
                            'stream_id': msg_id
                        })
                        
                        # Acknowledge message
                        await self.client.xack(stream_key, self.consumer_group, msg_id)
            
        except Exception as e:
            print(f"Redis Stream: Receive failed - {e}")
            
        return messages


class RedisLoadBalancedProtocol(RedisProtocol):
    """Redis Protocol with Load Balancing for single-delivery tasks"""
    
    def __init__(self, config: ConnectionConfig, consumer_id: str = None):
        super().__init__(config)
        self.consumer_id = consumer_id or f"consumer_{id(self)}"
        self.task_queues: Dict[str, bool] = {}  # Track which queues we're listening to
        
    async def publish_task(self, job: str, task: str, context: str, 
                          message: AetherMessage, shared: bool = True) -> bool:
        """Publish task with load balancing (single delivery)"""
        if shared and message.action == 'perform':
            topic = self.generate_topic(job, task, context, "", message.action, shared=True)
            return await self._push_task_to_queue(topic, message)
        else:
            # Use regular publish for non-task messages
            topic = self.generate_topic(job, task, context, "broadcast", message.action, shared=False)
            return await self.publish(topic, message)
    
    async def subscribe_to_tasks(self, job: str, task: str, context: str, 
                               callback: Callable[[AetherMessage], None]) -> bool:
        """Subscribe to load-balanced tasks (only one consumer gets each task)"""
        topic = self.generate_topic(job, task, context, "", "perform", shared=True)
        
        if topic in self.task_queues:
            return True
            
        self.task_queues[topic] = True
        
        # Start background task to poll from queue
        asyncio.create_task(self._consume_tasks(topic, callback))
        
        return True
    
    async def _consume_tasks(self, topic: str, callback: Callable[[AetherMessage], None]):
        """Background task consumer (blocking pop from Redis list)"""
        print(f"Redis: Started task consumer for {topic}")
        
        while self.connected and topic in self.task_queues:
            try:
                task_data = await self._pop_task_from_queue(topic)
                
                if task_data:
                    # Parse and call callback
                    message = AetherMessage.from_json(task_data['message'])
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(message)
                            else:
                                callback(message)
                        except Exception as e:
                            print(f"Redis: Task callback failed - {e}")
                
            except Exception as e:
                print(f"Redis: Task consumer error - {e}")
                await asyncio.sleep(1)  # Brief pause before retry
        
        print(f"Redis: Stopped task consumer for {topic}")
    
    async def unsubscribe_from_tasks(self, job: str, task: str, context: str) -> bool:
        """Stop consuming tasks from queue"""
        topic = self.generate_topic(job, task, context, "", "perform", shared=True)
        
        if topic in self.task_queues:
            del self.task_queues[topic]
            return True
            
        return False