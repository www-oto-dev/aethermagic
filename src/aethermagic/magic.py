"""
Enhanced AetherMagic with Multi-Protocol Support
"""

import threading
from uuid import uuid1
import json
import socket
import asyncio
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from .protocols import (
    ProtocolInterface, ConnectionConfig, AetherMessage, ProtocolType,
    SUBSTATE
)

# Import protocol implementations
from .protocols.redis_protocol import RedisProtocol, RedisStreamProtocol
from .protocols.websocket_protocol import WebSocketProtocol
from .protocols.zeromq_protocol import ZeroMQProtocol
from .protocols.mqtt_protocol import MQTTProtocol


class ProtocolFactory:
    """Factory for creating protocol instances"""
    
    @staticmethod
    def create_protocol(config: ConnectionConfig, **kwargs) -> ProtocolInterface:
        """Create appropriate protocol instance based on config"""
        
        if config.protocol_type == ProtocolType.MQTT:
            return MQTTProtocol(config)
            
        elif config.protocol_type == ProtocolType.REDIS:
            use_streams = config.extra_params.get('use_streams', False)
            if use_streams:
                consumer_group = config.extra_params.get('consumer_group', 'workers')
                consumer_name = config.extra_params.get('consumer_name', None)
                return RedisStreamProtocol(config, consumer_group, consumer_name)
            else:
                return RedisProtocol(config)
                
        elif config.protocol_type == ProtocolType.HTTP:
            mode = config.extra_params.get('mode', 'client')
            return WebSocketProtocol(config, mode)
            
        elif config.protocol_type == ProtocolType.WEBSOCKET:
            mode = config.extra_params.get('mode', 'client')  
            return WebSocketProtocol(config, mode)
            
        elif config.protocol_type == ProtocolType.ZEROMQ:
            pattern = config.extra_params.get('pattern', 'pubsub')
            return ZeroMQProtocol(config, pattern)
            
        else:
            raise ValueError(f"Unsupported protocol: {config.protocol_type}")


# MQTTProtocolWrapper removed - using direct MQTTProtocol implementation


shared_instances = {}
shared_instances_lock = threading.Lock()


class MultiProtocolAetherMagic:
    """Enhanced AetherMagic with multiple protocol support and backward compatibility"""
    
    def __init__(self, 
                 protocol_type: Union[ProtocolType, str] = None,
                 host: str = None,
                 port: int = None,
                 ssl: bool = False,
                 username: str = '',
                 password: str = '',
                 union: str = 'default',
                 channel: str = '',
                 # Backward compatibility parameters
                 server: str = None,
                 user: str = None,
                 **kwargs):
        
        # Backward compatibility: map old parameters to new ones
        if server is not None:
            host = server
            protocol_type = ProtocolType.MQTT
        if user is not None:
            username = user
        
        # Set defaults based on protocol
        if protocol_type is None:
            protocol_type = ProtocolType.MQTT
        if host is None:
            host = 'localhost'
        if port is None:
            if protocol_type == ProtocolType.MQTT:
                port = 1883
            elif protocol_type == ProtocolType.REDIS:
                port = 6379
            elif protocol_type == ProtocolType.WEBSOCKET:
                port = 8080
            elif protocol_type == ProtocolType.ZEROMQ:
                port = 5555
            else:
                port = 1883
        
        self.__listeners = []
        self.__outgoing = []
        self.__incoming = []
        self.__subscribed = []

        # Convert string to enum if needed
        if isinstance(protocol_type, str):
            protocol_type = ProtocolType(protocol_type)
        
        # Create configuration
        self.config = ConnectionConfig(
            protocol_type=protocol_type,
            host=host,
            port=port,
            ssl=ssl,
            username=username,
            password=password,
            union=union,
            channel=channel,
            extra_params=kwargs
        )
        
        # Create protocol instance
        self.protocol = ProtocolFactory.create_protocol(self.config, **kwargs)
        
        self.__hostname = socket.gethostname()
        self.__identifier = str(uuid1())
        
        self.__share_tasks = True
        self.__action_in_topic = True
        self.__connected = False
        self.__should_stop = False  # Flag to stop main loop
        self.__temp_unsubscribed_shared = []  # Track temporarily unsubscribed shared topics
        self.__processed_tasks = set()  # Track processed task IDs to prevent duplicates
        
        # Share instance with thread and optional channel
        self.__share_instance(self)
    
    def __share_instance(self, instance):
        """Store shared instance keyed by (threadid, channel).

        We key by tuple (threadid, channel) so a single thread can host
        multiple AetherMagic instances differentiated by channel.
        For backward compatibility, an instance with empty channel will
        also be stored under the raw thread id key.
        """
        global shared_instances, shared_instances_lock

        with shared_instances_lock:
            threadid = threading.get_ident()
            channel = ''
            if instance is not None and hasattr(instance, 'config'):
                channel = getattr(instance.config, 'channel', '') or ''

            # Store under composite key
            shared_instances[(threadid, channel)] = instance
            
            # Store under raw thread id only if no default instance exists yet
            # First created instance becomes the default for AetherTask without channel
            if threadid not in shared_instances:
                shared_instances[threadid] = instance
    
    @staticmethod
    def shared(channel: str = ''):
        """Get shared instance for current thread and optional channel.

        If channel is provided, this looks up the instance stored under
        (threadid, channel). If not found and channel is empty it falls
        back to the legacy thread-only key for backward compatibility.
        """
        instance = None
        global shared_instances, shared_instances_lock

        with shared_instances_lock:
            threadid = threading.get_ident()
            key = (threadid, channel or '')
            if key in shared_instances:
                instance = shared_instances[key]
            elif channel == '' and threadid in shared_instances:
                # Legacy fallback
                instance = shared_instances[threadid]

        return instance
    
    async def main(self):
        """Main connection and message processing loop"""
        failed_connection_interval = 10
        
        while not self.__should_stop:
            just_connected = True
            
            try:
                # Connect to protocol service
                success = await self.protocol.connect()
                if not success:
                    raise Exception("Failed to connect")
                
                print(f"{self.config.protocol_type.value.upper()}: Connected")
                self.__connected = True
                
                while self.__connected and not self.__should_stop:
                    # Send online status if just connected
                    if just_connected:
                        await self.online("system", "", "online", self.__hostname, self.__identifier, {}, None)
                        just_connected = False
                    
                    # Subscribe to required listeners
                    await self.__subscribe_required_listeners()
                    
                    # Receive incoming messages
                    has_new_incoming = await self.__receive_incoming()
                    
                    # Reply immediately for some incoming messages
                    await self.__reply_incoming_immediate()
                    
                    # Send outgoing messages
                    await self.__send_outgoing()
                    
                    # Unsubscribe as needed
                    await self.__unsubscribe_required_listeners()
                    
                    # Process incoming messages
                    if len(self.__incoming) > 0:
                        # Process messages without unsubscribing
                        # Use message deduplication instead
                        await self.__process_incoming()
                    
                    # Brief sleep
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"{self.config.protocol_type.value.upper()}: Connection lost - {e}")
                self.__connected = False
                await asyncio.sleep(failed_connection_interval)
        
        # Clean shutdown
        if self.__connected:
            await self.protocol.disconnect()
            print(f"{self.config.protocol_type.value.upper()}: Disconnected")
    
    async def stop(self):
        """Stop the main loop gracefully"""
        print(f"{self.config.protocol_type.value.upper()}: Stopping...")
        self.__should_stop = True
        self.__connected = False
    
    async def disconnect(self):
        """Disconnect from protocol service"""
        if self.__connected:
            await self.protocol.disconnect()
            self.__connected = False
    
    async def __subscribe_required_listeners(self):
        """Subscribe to topics for all listeners that need it"""
        for listener in self.__listeners:
            if listener['state'] == SUBSTATE.TO_SUBSCRIBE:
                topic = self.__topic_for_listener(listener)
                
                if not any(topic == s for s in self.__subscribed):
                    print(f"{self.config.protocol_type.value.upper()}: Subscribed to {topic}")
                    await self.protocol.subscribe(topic)
                    self.__subscribed.append(topic)
                
                listener['state'] = SUBSTATE.SUBSCRIBED
    
    async def __unsubscribe_required_listeners(self):
        """Unsubscribe from topics that are no longer needed"""
        for listener in self.__listeners:
            if listener['state'] == SUBSTATE.TO_UNSUBSCRIBE:
                topic = self.__topic_for_listener(listener)
                listener['state'] = SUBSTATE.UNSUBSCRIBED
                
                # Check if any other listener still needs this topic
                found = False
                for check in self.__listeners:
                    checktopic = self.__topic_for_listener(check)
                    if (topic == checktopic and 
                        not (check['state'] == SUBSTATE.TO_UNSUBSCRIBE or 
                             check['state'] == SUBSTATE.UNSUBSCRIBED)):
                        found = True
                
                if not found and topic in self.__subscribed:
                    print(f"{self.config.protocol_type.value.upper()}: Unsubscribed from {topic}")
                    await self.protocol.unsubscribe(topic)
                    self.__subscribed.remove(topic)
    
    async def __unsubscribe_shared_subscriptions(self):
        """Unsubscribe from shared subscriptions temporarily"""
        if not hasattr(self, '__temp_unsubscribed_shared'):
            self.__temp_unsubscribed_shared = []
        
        # Clear previous list
        self.__temp_unsubscribed_shared = []
        
        for topic in list(self.__subscribed):  # Use list() to avoid modification during iteration
            if topic.startswith('$share/') or 'shared.' in topic:
                await self.protocol.unsubscribe(topic)
                self.__temp_unsubscribed_shared.append(topic)
                self.__subscribed.remove(topic)
                print(f"MQTT: Temporarily unsubscribed from {topic} (saved for re-subscription)")
    
    async def __resubscribe_shared_subscriptions(self):
        """Re-subscribe to shared subscriptions after processing"""
        if hasattr(self, '__temp_unsubscribed_shared') and self.__temp_unsubscribed_shared:
            print(f"MQTT: Re-subscribing to {len(self.__temp_unsubscribed_shared)} shared subscriptions")
            for topic in self.__temp_unsubscribed_shared:
                await self.protocol.subscribe(topic)
                self.__subscribed.append(topic)
                print(f"MQTT: Re-subscribed to {topic}")
            
            self.__temp_unsubscribed_shared = []
        else:
            print(f"MQTT: No temp unsubscribed list found (hasattr: {hasattr(self, '__temp_unsubscribed_shared')}, list: {getattr(self, '__temp_unsubscribed_shared', 'N/A')})")
    
    async def __receive_incoming(self) -> bool:
        """Receive incoming messages from protocol"""
        has_new_incoming = False
        
        try:
            messages = await self.protocol.receive_messages()
            
            for msg in messages:
                topic = msg['topic']
                payload = msg['payload']
                
                if topic and payload:
                    
                    print(f"{self.config.protocol_type.value.upper()}: Received {topic}")
                    
                    incoming = {'topic': topic, 'payload': payload}
                    self.__incoming.append(incoming)
                    has_new_incoming = True
        
        except Exception as e:
            print(f"Receive error: {e}")
        
        return has_new_incoming
    
    async def __send_outgoing(self):
        """Send all queued outgoing messages"""
        for outgoing in self.__outgoing:
            topic = outgoing['topic']
            payload_str = outgoing['payload']
            retain = outgoing['retain']
            
            try:
                # Parse payload to create AetherMessage
                payload_data = json.loads(payload_str)
                message = AetherMessage.from_dict(payload_data)
                
                print(f"{self.config.protocol_type.value.upper()}: Sending {topic}")
                await self.protocol.publish(topic, message, retain)
                
            except Exception as e:
                print(f"Send error: {e}")
        
        self.__outgoing = []
    
    def __topic_for_listener(self, listener) -> str:
        """Generate topic string for a listener - restore original shared subscription logic"""
        # For subscription, use wildcard '+' for perform actions to catch any tid
        tid_for_subscription = '+' if listener['action'] == 'perform' else listener['tid']
        
        # IMPORTANT: Also update the listener's TID to wildcard for perform actions
        # This ensures proper matching in __for_message_fits_listener
        if listener['action'] == 'perform' and listener['tid'] not in ['+', '']:
            print(f"MQTT: Converting listener TID from {listener['tid']} to + for perform action")
            listener['tid'] = '+'
        
        # Use shared subscriptions for perform actions (task distribution)
        use_shared = listener['action'] == 'perform' and self.__share_tasks
        
        return self.protocol.generate_topic(
            listener['job'],
            listener['task'], 
            listener['context'],
            tid_for_subscription,  # Use '+' for perform subscriptions
            listener['action'],
            shared=use_shared,  # Enable shared subscriptions for task distribution
            workgroup=listener['workgroup']
        )
    
    def __data_to_fulldata(self, action, status, progress, data):
        """Convert data to full message format"""
        return {
            "host": self.__hostname,
            "client": self.__identifier,
            "action": action,
            "status": status,
            "progress": progress,
            "data": data,
        }
    
    def __data_to_payload(self, action, status, progress, data):
        """Convert data to JSON payload"""
        fulldata = self.__data_to_fulldata(action, status, progress, data)
        return json.dumps(fulldata)
    
    def __payload_to_fulldata(self, payload):
        """Parse JSON payload to full data"""
        try:
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')
            fulldata = json.loads(payload)
        except Exception as err:
            print(f"JSON parsing error {err}")
            fulldata = self.__data_to_fulldata('complete', 'failed', 0, {})
        return fulldata
    
    def __incoming_parts(self, incoming):
        """Extract components from incoming message"""
        topic = incoming['topic']
        payload = incoming['payload']
        
        fulldata = self.__payload_to_fulldata(payload)
        data = fulldata['data']
        
        # Parse topic using protocol's parser
        parts = self.protocol.parse_topic(topic)
        
        union = parts.get('union', '')
        job = parts.get('job', '')
        task = parts.get('task', '')
        context = parts.get('context', '')
        tid = parts.get('tid', '')
        action = fulldata.get('action', parts.get('action', ''))
        
        return topic, payload, fulldata, data, union, job, task, context, tid, action
    
    async def __detect_perform(self) -> bool:
        """Check if any incoming message is a 'perform' action"""
        for incoming in self.__incoming:
            _, _, _, _, _, _, _, _, _, action = self.__incoming_parts(incoming)
            if action == 'perform':
                return True
        return False
    
    async def __reply_incoming_immediate(self):
        """Send immediate replies for certain message types"""
        async def reply(incoming, listener):
            topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts(incoming)
            
            if action == 'perform':
                # Send progress 0 to acknowledge task receipt
                await self.status(job, "", task, context, tid, {}, None, 0, immediate=False)
        
        for incoming in self.__incoming:
            await self.__for_message_fits_listener(incoming, reply)
    
    async def __process_incoming(self):
        """Process all incoming messages with deduplication"""
        async def handle(incoming, listener):
            topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts(incoming)
            
            # Deduplicate perform actions by task ID
            if action == 'perform':
                task_key = f"{job}:{task}:{context}:{tid}"
                if task_key in self.__processed_tasks:
                    return
                else:
                    self.__processed_tasks.add(task_key)
            
            handler = listener['handler']
            if handler is not None:
                # Check if handler is async function
                if asyncio.iscoroutinefunction(handler):
                    await handler(action, tid, data, fulldata)
                else:
                    # Call regular function directly
                    handler(action, tid, data, fulldata)
        
        for incoming in self.__incoming:
            await self.__for_message_fits_listener(incoming, handle)
        
        self.__incoming = []
    
    async def __for_message_fits_listener(self, incoming, callback):
        """Check if incoming message fits any listener and call callback"""
        topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts(incoming)
        
        if task and action and union == self.config.union:
            for listener in self.__listeners:
                if listener['state'] != SUBSTATE.TO_UNSUBSCRIBE:
                    if (listener['job'] == job and 
                        listener['task'] == task and 
                        listener['context'] == context and 
                        listener['action'] == action):
                        
                        # Check TID matching: exact match OR wildcard ('+') OR empty string (legacy wildcard)
                        if tid == listener['tid'] or listener['tid'] == '+' or listener['tid'] == '':
                            await callback(incoming, listener)
    
    async def __send_to_queue(self, job, workgroup, task, context, action, tid, payload, retain=False):
        """Add message to outgoing queue"""
        topic = self.protocol.generate_topic(job, task, context, tid, action)
        self.__outgoing.append({
            'topic': topic, 
            'payload': payload, 
            'retain': retain
        })
    
    async def __send_immediate(self, job, workgroup, task, context, action, tid, payload, retain=False):
        """Send message immediately"""
        if self.__connected:
            try:
                topic = self.protocol.generate_topic(job, task, context, tid, action)
                
                # Parse payload to create AetherMessage
                payload_data = json.loads(payload)
                message = AetherMessage.from_dict(payload_data)
                
                await self.protocol.publish(topic, message, retain)
                await asyncio.sleep(0.001)  # Brief yield
                
            except Exception as e:
                print(f"Immediate send failed: {e}")
                self.__connected = False
                await self.__send_to_queue(job, workgroup, task, context, action, tid, payload, retain)
        else:
            await self.__send_to_queue(job, workgroup, task, context, action, tid, payload, retain)
    
    async def __send(self, job, workgroup, task, context, action, tid, payload, retain=False, immediate=False):
        """Send message either immediately or to queue"""
        if immediate:
            await self.__send_immediate(job, workgroup, task, context, action, tid, payload, retain=retain)
        else:
            await self.__send_to_queue(job, workgroup, task, context, action, tid, payload, retain=retain)
    
    # Public API methods (same as original)
    async def idle(self, job, workgroup, task, context, tid, data, on_handle, immediate=False):
        if on_handle is not None:
            await self.subscribe(job, workgroup, task, context, tid, 'perform', on_handle)
        payload = self.__data_to_payload('idle', 'online', 100, data)
        await self.__send(job, workgroup, task, context, 'idle', tid, payload, retain=False, immediate=immediate)
    
    async def perform(self, job, workgroup, task, context, tid, data, on_handle, immediate=False):
        if on_handle is not None:
            await self.subscribe(job, workgroup, task, context, tid, 'status', on_handle)
            await self.subscribe(job, workgroup, task, context, tid, 'complete', on_handle)
        payload = self.__data_to_payload('perform', 'initialized', 0, data)
        await self.__send(job, workgroup, task, context, 'perform', tid, payload, retain=False, immediate=immediate)
    
    async def complete(self, job, workgroup, task, context, tid, data, on_handle, success=True, immediate=False):
        result = 'succeed' if success else 'failed'
        payload = self.__data_to_payload('complete', result, 100, data)
        await self.__send(job, workgroup, task, context, 'complete', tid, payload, retain=False, immediate=immediate)
    
    async def status(self, job, workgroup, task, context, tid, data, on_handle, progress=0, immediate=False):
        payload = self.__data_to_payload('status', 'progress', progress, data)
        await self.__send(job, workgroup, task, context, 'status', tid, payload, retain=False, immediate=immediate)
    
    async def dismiss(self, job, workgroup, task, context, tid, data, on_handle, immediate=False):
        if on_handle is not None:
            await self.unsubscribe(job, workgroup, task, context, tid, 'complete', on_handle)
        payload = self.__data_to_payload('dismiss', 'dismissed', 100, data)
        await self.__send(job, workgroup, task, context, 'dismiss', tid, payload, retain=False, immediate=immediate)
    
    async def online(self, job, workgroup, task, context, tid, data, on_handle):
        payload = self.__data_to_payload('online', 'connected', 100, data)
        await self.__send(job, workgroup, task, context, 'online', tid, payload, retain=False)
    
    async def subscribe(self, job, workgroup, task, context, tid, action, handler_func):
        if handler_func is not None:
            self.__listeners.append({
                'job': job,
                'workgroup': workgroup, 
                'task': task,
                'context': context,
                'tid': tid,
                'action': action,
                'state': SUBSTATE.TO_SUBSCRIBE,
                'handler': handler_func
            })
    
    async def unsubscribe(self, job, workgroup, task, context, tid, action, handler_func):
        for listener in self.__listeners:
            if (listener['job'] == job and 
                listener['task'] == task and 
                listener['context'] == context and 
                listener['action'] == action and 
                listener['handler'] == handler_func):
                listener['state'] = SUBSTATE.TO_UNSUBSCRIBE
    
    # New methods for load balancing support
    async def perform_task(self, job: str, task: str, context: str, data: dict, 
                          shared: bool = False, immediate: bool = False):
        """Perform task with optional load balancing"""
        tid = f"task_{id(data)}"
        payload = self.__data_to_payload('perform', 'initialized', 0, data)
        
        if shared:
            # Use shared subscription approach for load balancing
            await self.__send_shared(job, task, context, 'perform', tid, payload, retain=False, immediate=immediate)
        else:
            await self.__send(job, "default", task, context, 'perform', tid, payload, retain=False, immediate=immediate)
    
    async def add_task(self, job: str, task: str, context: str, callback, shared: bool = False):
        """Add task handler with optional load balancing"""
        if shared:
            # Subscribe to shared topic for load balancing
            await self.subscribe_shared(job, task, context, 'perform', callback)
        else:
            tid = f"worker_{id(self)}"
            await self.subscribe(job, "default", task, context, tid, 'perform', callback)
    
    async def __send_shared(self, job: str, task: str, context: str, action: str, 
                           tid: str, payload: dict, retain: bool = False, immediate: bool = False):
        """Send message using shared subscription for load balancing"""
        topic = self.protocol.generate_topic(job, task, context, tid, action, shared=True)
        message = AetherMessage(
            action=action,
            data=payload,
            source=self.client_id
        )
        
        if immediate or self.__connected:
            await self.protocol.publish(topic, message, retain=retain)
        else:
            # Queue for later sending when connected
            self.__outgoing.append({
                'topic': topic,
                'message': message,
                'retain': retain
            })
    
    async def subscribe_shared(self, job: str, task: str, context: str, action: str, callback):
        """Subscribe using shared subscription for load balancing"""
        # Add listener for shared subscription
        self.__listeners.append({
            'job': job,
            'workgroup': "shared",  # Use shared workgroup for load balancing
            'task': task,
            'context': context,
            'tid': "+",  # Use wildcard for shared subscriptions to match any tid
            'action': action,
            'handler': callback,
            'state': SUBSTATE.TO_SUBSCRIBE
        })
        
        # Subscribe to shared topic
        topic = self.protocol.generate_topic(job, task, context, "", action, shared=True)
        return await self.protocol.subscribe(topic, callback)


class AetherMagic(MultiProtocolAetherMagic):
    """
    Main AetherMagic class with full backward compatibility
    Supports both old MQTT-only initialization and new multi-protocol initialization
    """
    
    def __init__(self, server=None, port=None, ssl=None, user=None, password=None, union=None, 
                 protocol_type=None, host=None, channel=None, **kwargs):
        
        # Old initialization style (MQTT only) - highest priority
        if server is not None:
            super().__init__(
                protocol_type=ProtocolType.MQTT,
                host=server,
                port=port or 1883,
                ssl=ssl or False,
                username=user or '',
                password=password or '',
                union=union or 'default',
                channel=channel or '',
                **kwargs
            )
        
        # New initialization style (multi-protocol)
        elif protocol_type is not None:
            super().__init__(
                protocol_type=protocol_type,
                host=host or 'localhost',
                port=port or (1883 if protocol_type == ProtocolType.MQTT else 6379),
                ssl=ssl or False,
                username=user or '',
                password=password or '',
                union=union or 'default',
                channel=channel or '',
                **kwargs
            )
        
        # Default to MQTT for full backward compatibility
        else:
            super().__init__(
                protocol_type=ProtocolType.MQTT,
                host=host or 'localhost',
                port=port or 1883,
                ssl=ssl or False,
                username=user or '',
                password=password or '',
                union=union or 'default',
                channel=channel or '',
                **kwargs
            )