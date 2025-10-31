#!/usr/bin/env python3
"""
Quick Start: AetherMagic Multi-Protocol Setup

Minimal example showing MQTT + Redis configuration in one service
"""

import os
from aethermagic import AetherMagic, AetherTask

# =============================================================================
# 1. CONFIGURATION
# =============================================================================

# MQTT Configuration
MQTT_CONFIG = {
    "protocol_type": "mqtt",
    "host": os.getenv("MQTT_HOST", "localhost"),
    "port": int(os.getenv("MQTT_PORT", "1883")),
    "username": os.getenv("MQTT_USER", ""),
    "password": os.getenv("MQTT_PASS", ""),
    "union": "production",
    "channel": "mqtt"  # 🔥 Unique channel identifier
}

# Redis Configuration  
REDIS_CONFIG = {
    "protocol_type": "redis",
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "password": os.getenv("REDIS_PASS", ""),
    "union": "production", 
    "channel": "redis",  # 🔥 Unique channel identifier
    "use_streams": False  # Redis-specific option
}

# =============================================================================
# 2. INITIALIZATION
# =============================================================================

# Create AetherMagic instances
mqtt_service = AetherMagic(**MQTT_CONFIG)
redis_service = AetherMagic(**REDIS_CONFIG)

print("✅ MQTT service initialized on channel 'mqtt'")
print("✅ Redis service initialized on channel 'redis'")

# =============================================================================
# 3. USAGE
# =============================================================================

# Create tasks for different channels
mqtt_task = AetherTask(
    job="notifications",
    task="send_email", 
    context="user_signup",
    channel="mqtt"  # 🔥 Will use MQTT AetherMagic
)

redis_task = AetherTask(
    job="caching",
    task="store_session",
    context="user_data", 
    channel="redis"  # 🔥 Will use Redis AetherMagic
)

# Task without channel - uses fallback (latest created AetherMagic)
fallback_task = AetherTask(
    job="general",
    task="log_event",
    context="system"
    # No channel - uses thread-level fallback
)

print("✅ Tasks created for different channels")
print("✅ Multi-protocol microservice ready!")

# =============================================================================
# 4. ADVANCED: Factory Pattern (Optional)
# =============================================================================

class MultiProtocolService:
    """Service manager for multiple AetherMagic protocols"""
    
    def __init__(self):
        self.services = {}
        
    def add_service(self, name: str, config: dict):
        """Add AetherMagic service with config"""
        self.services[name] = AetherMagic(**config)
        return self.services[name]
    
    def get_service(self, name: str):
        """Get AetherMagic service by name"""
        return self.services.get(name)
    
    def create_task(self, service_name: str, job: str, task: str, context: str = "default"):
        """Create AetherTask for specific service"""
        service = self.services[service_name]
        return AetherTask(
            job=job,
            task=task,
            context=context,
            channel=service.config.channel
        )

# Usage example:
# service_manager = MultiProtocolService()
# service_manager.add_service("messaging", MQTT_CONFIG)  
# service_manager.add_service("caching", REDIS_CONFIG)
# 
# task = service_manager.create_task("messaging", "alerts", "send_sms")