"""
MQTT Protocol Implementation for AetherMagic
Original MQTT implementation moved to protocol architecture
"""

import asyncio
import json
import certifi
import socket
from uuid import uuid1
from typing import Optional, Callable, Dict, Any, List
import paho.mqtt.client as mqtt
import aiomqtt

from . import ProtocolInterface, ConnectionConfig, AetherMessage, ProtocolType


class MQTTProtocol(ProtocolInterface):
    """MQTT protocol implementation using aiomqtt"""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.mqtt_client: Optional[aiomqtt.Client] = None
        self.subscribed_topics: set = set()
        self.hostname = socket.gethostname()
        self.client_id = str(uuid1())
        self.share_tasks = True
        self.action_in_topic = True
        
    async def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            # Setup TLS parameters if SSL enabled
            tls_params = None
            if self.config.ssl:
                tls_params = aiomqtt.TLSParameters(ca_certs=certifi.where())
            
            # Create MQTT client
            self.mqtt_client = aiomqtt.Client(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username if self.config.username else None,
                password=self.config.password if self.config.username else None,
                identifier=self.client_id,
                tls_context=None,
                tls_params=tls_params,
                timeout=self.config.timeout,
                keepalive=self.config.keepalive,
                clean_session=True,
            )
            
            # Test connection by entering context
            await self.mqtt_client.__aenter__()
            
            self.connected = True
            print(f"MQTT: Connected to {self.config.host}:{self.config.port}")
            return True
            
        except Exception as e:
            print(f"MQTT: Connection failed - {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from MQTT broker"""
        try:
            if self.mqtt_client:
                await self.mqtt_client.__aexit__(None, None, None)
            self.connected = False
            return True
        except Exception as e:
            print(f"MQTT: Disconnect failed - {e}")
            return False
    
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish message to MQTT topic"""
        try:
            if not self.mqtt_client or not self.connected:
                return False
            
            payload = message.to_json()
            await self.mqtt_client.publish(topic, payload, retain=retain)
            return True
            
        except Exception as e:
            print(f"MQTT: Publish failed - {e}")
            return False
    
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to MQTT topic"""
        try:
            if not self.mqtt_client or not self.connected:
                return False
            
            await self.mqtt_client.subscribe(topic)
            self.subscribed_topics.add(topic)
            return True
            
        except Exception as e:
            print(f"MQTT: Subscribe failed - {e}")
            return False
    
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from MQTT topic"""
        try:
            if not self.mqtt_client or not self.connected:
                return False
            
            await self.mqtt_client.unsubscribe(topic)
            self.subscribed_topics.discard(topic)
            return True
            
        except Exception as e:
            print(f"MQTT: Unsubscribe failed - {e}")
            return False
    
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive messages from subscribed topics"""
        messages = []
        
        if not self.mqtt_client or not self.connected:
            return messages
        
        try:
            # Check for messages with timeout
            if len(self.mqtt_client.messages) > 0:
                async for message in self.mqtt_client.messages:
                    topic = str(message.topic)
                    payload = message.payload
                    
                    if topic and payload and payload != b'':
                        messages.append({
                            'topic': topic,
                            'payload': payload.decode('utf-8') if isinstance(payload, bytes) else payload
                        })
                    
                    # Break after processing available messages
                    if len(self.mqtt_client.messages) == 0:
                        break
                        
        except Exception as e:
            print(f"MQTT: Receive failed - {e}")
        
        return messages
    
    def generate_topic(self, job: str, task: str, context: str, tid: str, action: str, shared: bool = False, workgroup: str = "") -> str:
        """Generate MQTT topic matching original format with shared subscriptions"""
        
        # Base topic format: union/job/task/context/tid/action
        base_topic = f'{self.config.union}/{job}/{task}/{context}/{tid}'
        
        if self.action_in_topic:
            base_topic = f'{base_topic}/{action}'
        
        # For shared subscriptions (load balancing for perform actions)
        if shared and action == 'perform' and self.share_tasks and workgroup:
            # Example format: $share/union_job_workgroup/union/job/task/context/+/perform
            shared_group = f'{self.config.union}_{job}_{workgroup}'
            topic = f'$share/{shared_group}/{base_topic}'
        else:
            topic = base_topic
        
        return topic
    
    async def send_online_message(self):
        """Send online status message"""
        try:
            online_message = AetherMessage(
                action='online',
                status='connected',
                progress=100,
                data={},
                host=self.hostname,
                client=self.client_id
            )
            
            topic = self.generate_topic(
                'system', '', 'online', self.hostname, 'online'
            )
            
            await self.publish(topic, online_message)
            
        except Exception as e:
            print(f"MQTT: Failed to send online message - {e}")


class MQTTBrokerEmulator:
    """MQTT broker emulator with proper shared subscription support"""
    
    def __init__(self, port: int = 1883):
        self.port = port
        self.clients: Dict[str, Dict] = {}
        self.subscriptions: Dict[str, List] = {}  # Regular subscriptions: topic -> [client_ids]
        self.shared_subscriptions: Dict[str, Dict] = {}  # Shared subscriptions: group -> {topic: [client_ids]}
        self.shared_round_robin: Dict[str, int] = {}  # Round robin counters: topic -> index
        self.running = False
    
    async def start(self):
        """Start the broker emulator"""
        print(f"MQTT Broker Emulator started on port {self.port}")
        self.running = True
        
        # Simple message routing loop
        while self.running:
            await asyncio.sleep(0.1)
            # In a real implementation, this would handle client connections
            # and message routing between them
    
    async def stop(self):
        """Stop the broker emulator"""
        self.running = False
        print("MQTT Broker Emulator stopped")
    
    def add_client(self, client_id: str, client_info: Dict):
        """Add client to broker"""
        self.clients[client_id] = client_info
    
    def remove_client(self, client_id: str):
        """Remove client from broker"""
        if client_id in self.clients:
            del self.clients[client_id]
    
    def subscribe_client(self, client_id: str, topic: str):
        """Subscribe client to topic (handles both regular and shared subscriptions)"""
        if topic.startswith('$share/'):
            # Shared subscription: $share/group/actual_topic
            parts = topic[7:].split('/', 1)  # Remove $share/
            if len(parts) >= 2:
                group = parts[0]
                actual_topic = parts[1]
                
                if group not in self.shared_subscriptions:
                    self.shared_subscriptions[group] = {}
                
                if actual_topic not in self.shared_subscriptions[group]:
                    self.shared_subscriptions[group][actual_topic] = []
                
                if client_id not in self.shared_subscriptions[group][actual_topic]:
                    self.shared_subscriptions[group][actual_topic].append(client_id)
                    print(f"MQTT Broker: Added {client_id} to shared group '{group}' for topic '{actual_topic}'")
        else:
            # Regular subscription
            if topic not in self.subscriptions:
                self.subscriptions[topic] = []
            
            if client_id not in self.subscriptions[topic]:
                self.subscriptions[topic].append(client_id)
    
    def unsubscribe_client(self, client_id: str, topic: str):
        """Unsubscribe client from topic (handles both regular and shared subscriptions)"""
        if topic.startswith('$share/'):
            # Shared subscription: $share/group/actual_topic
            parts = topic[7:].split('/', 1)  # Remove $share/
            if len(parts) >= 2:
                group = parts[0]
                actual_topic = parts[1]
                
                if (group in self.shared_subscriptions and 
                    actual_topic in self.shared_subscriptions[group] and
                    client_id in self.shared_subscriptions[group][actual_topic]):
                    self.shared_subscriptions[group][actual_topic].remove(client_id)
        else:
            # Regular subscription
            if topic in self.subscriptions and client_id in self.subscriptions[topic]:
                self.subscriptions[topic].remove(client_id)
    
    async def publish_message(self, topic: str, payload: str, retain: bool = False):
        """Publish message to subscribers (with proper shared subscription load balancing)"""
        subscribers = []
        
        # Check regular subscriptions first
        for sub_topic, clients in self.subscriptions.items():
            if self._topic_matches(topic, sub_topic):
                subscribers.extend(clients)
        
        # Check shared subscriptions - only send to ONE client per group
        for group, group_subscriptions in self.shared_subscriptions.items():
            for shared_topic, clients in group_subscriptions.items():
                if self._topic_matches(topic, shared_topic) and clients:
                    # Load balance: pick next client in round-robin fashion
                    key = f"{group}:{shared_topic}"
                    if key not in self.shared_round_robin:
                        self.shared_round_robin[key] = 0
                    
                    # Get the next client
                    client_index = self.shared_round_robin[key] % len(clients)
                    selected_client = clients[client_index]
                    subscribers.append(selected_client)
                    
                    # Update round robin counter
                    self.shared_round_robin[key] = (self.shared_round_robin[key] + 1) % len(clients)
                    
                    print(f"MQTT Broker: Load balancing to {selected_client} (group: {group}, {client_index + 1}/{len(clients)})")
        
        # Route message to subscribers
        for client_id in subscribers:
            if client_id in self.clients:
                # In real implementation, would send to actual client
                print(f"MQTT Broker: Routing message to {client_id}: {topic} -> {payload[:50]}...")
    
    def _topic_matches(self, published_topic: str, subscription_topic: str) -> bool:
        """Check if published topic matches subscription pattern"""
        # Simple wildcard matching
        if subscription_topic.endswith('/#'):
            prefix = subscription_topic[:-2]
            return published_topic.startswith(prefix)
        elif '+' in subscription_topic:
            # Single level wildcard matching
            pub_parts = published_topic.split('/')
            sub_parts = subscription_topic.split('/')
            
            if len(pub_parts) != len(sub_parts):
                return False
            
            for pub_part, sub_part in zip(pub_parts, sub_parts):
                if sub_part != '+' and sub_part != pub_part:
                    return False
            return True
        else:
            return published_topic == subscription_topic