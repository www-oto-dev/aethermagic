"""
AetherMagic Protocol Interfaces
Multi-protocol communication system for microservices
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any, List
import asyncio
import json
from dataclasses import dataclass, asdict
from enum import Enum


class SUBSTATE:
    """Subscription states"""
    TO_SUBSCRIBE, SUBSCRIBED, TO_UNSUBSCRIBE, UNSUBSCRIBED = range(4)


class ProtocolType(Enum):
    MQTT = "mqtt"
    REDIS = "redis"  
    HTTP = "http"
    WEBSOCKET = "websocket"
    ZEROMQ = "zeromq"
    RABBITMQ = "rabbitmq"


class MessageType(Enum):
    IDLE = "idle"
    PERFORM = "perform"
    STATUS = "status"
    COMPLETE = "complete"
    ONLINE = "online"
    DISMISS = "dismiss"


@dataclass
class AetherMessage:
    """Unified message structure for all protocols"""
    action: str
    status: str
    progress: int
    data: Dict[str, Any]
    host: str
    client: str
    job: str = ""
    workgroup: str = ""
    task: str = ""
    context: str = ""
    tid: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AetherMessage':
        return cls(**data)
    
    @classmethod 
    def from_json(cls, json_str: str) -> 'AetherMessage':
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ConnectionConfig:
    """Base configuration for all protocols"""
    protocol_type: ProtocolType
    host: str
    port: int
    ssl: bool = False
    username: str = ""
    password: str = ""
    union: str = "default"
    channel: str = ""
    timeout: int = 10
    keepalive: int = 60
    extra_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class ProtocolInterface(ABC):
    """Abstract base class for all communication protocols"""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.connected = False
        self.listeners: List[Dict[str, Any]] = []
        self.outgoing_queue: List[Dict[str, Any]] = []
        self.incoming_queue: List[Dict[str, Any]] = []
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the protocol service"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to the protocol service"""
        pass
    
    @abstractmethod
    async def publish(self, topic: str, message: AetherMessage, retain: bool = False) -> bool:
        """Publish a message to a topic/channel"""
        pass
    
    @abstractmethod
    async def subscribe(self, topic: str, callback: Optional[Callable] = None) -> bool:
        """Subscribe to a topic/channel"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic/channel"""
        pass
    
    @abstractmethod
    async def receive_messages(self) -> List[Dict[str, Any]]:
        """Receive pending messages"""
        pass
    
    def generate_topic(self, job: str, task: str, context: str, tid: str, action: str, shared: bool = False, workgroup: str = "") -> str:
        """Generate topic string based on parameters"""
        if shared:
            shared_prefix = f"$share/{self.config.union}_{job}_{workgroup or 'default'}"
            topic = f"{shared_prefix}/{self.config.union}/{job}/{task}/{context}/{tid}/{action}"
        else:
            topic = f"{self.config.union}/{job}/{task}/{context}/{tid}/{action}"
        return topic
    
    def parse_topic(self, topic: str) -> Dict[str, str]:
        """Parse topic string to extract components"""
        parts = topic.split('/')
        
        # Handle shared subscription format
        if topic.startswith('$share/'):
            # Remove $share/group_name/ prefix
            parts = parts[2:]  # Skip $share and group_name
            
        if len(parts) >= 6:
            return {
                'union': parts[0],
                'job': parts[1], 
                'task': parts[2],
                'context': parts[3],
                'tid': parts[4],
                'action': parts[5]
            }
        return {}