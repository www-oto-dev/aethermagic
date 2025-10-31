#!/usr/bin/env python3
"""
AetherMagic Initialization from Configurations

This example shows different ways to initialize AetherMagic instances
from configuration files, environment variables, and structured configs.
"""

import asyncio
import sys
import os
import json

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

try:
    from aethermagic import AetherMagic, AetherTask, ProtocolType
except ImportError as e:
    print(f"Note: {e} (expected in demo environment)")

# Import our config examples
from config_examples import (
    MQTT_CONFIG, REDIS_CONFIG, 
    get_mqtt_config, get_redis_config,
    CONFIG_TEMPLATE, MQTT_PROD, REDIS_PROD
)

class AetherMagicFactory:
    """Factory for creating AetherMagic instances from configs"""
    
    @staticmethod
    def from_dict(config_dict):
        """Create AetherMagic from dictionary config"""
        return AetherMagic(**config_dict)
    
    @staticmethod
    def from_json_file(json_path, service_name):
        """Create AetherMagic from JSON config file"""
        with open(json_path, 'r') as f:
            config = json.load(f)
        
        service_config = config['aether_services'][service_name]
        
        # Flatten nested structure
        flat_config = {
            **service_config['connection'],
            **service_config['settings'],
            'protocol_type': service_config['protocol_type']
        }
        
        return AetherMagic(**flat_config)
    
    @staticmethod
    def from_yaml_file(yaml_path, service_name):
        """Create AetherMagic from YAML config file"""
        if not HAS_YAML:
            raise ImportError("PyYAML not installed. Run: pip install PyYAML")
            
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        
        service_config = config['aether_services'][service_name]
        
        flat_config = {
            **service_config['connection'],
            **service_config['settings'], 
            'protocol_type': service_config['protocol_type']
        }
        
        return AetherMagic(**flat_config)
    
    @staticmethod
    def from_env(prefix="AETHER"):
        """Create AetherMagic from environment variables"""
        protocol = os.getenv(f"{prefix}_PROTOCOL", "mqtt").lower()
        
        base_config = {
            "protocol_type": protocol,
            "host": os.getenv(f"{prefix}_HOST", "localhost"),
            "port": int(os.getenv(f"{prefix}_PORT", "1883" if protocol == "mqtt" else "6379")),
            "ssl": os.getenv(f"{prefix}_SSL", "false").lower() == "true",
            "username": os.getenv(f"{prefix}_USERNAME", ""),
            "password": os.getenv(f"{prefix}_PASSWORD", ""),
            "union": os.getenv(f"{prefix}_UNION", "default"),
            "channel": os.getenv(f"{prefix}_CHANNEL", protocol)
        }
        
        # Protocol-specific extras
        if protocol == "mqtt":
            base_config["keepalive"] = int(os.getenv(f"{prefix}_KEEPALIVE", "60"))
        elif protocol == "redis":
            base_config["use_streams"] = os.getenv(f"{prefix}_USE_STREAMS", "false").lower() == "true"
            if base_config["use_streams"]:
                base_config["consumer_group"] = os.getenv(f"{prefix}_CONSUMER_GROUP", "workers")
        
        return AetherMagic(**base_config)

def demo_config_initialization():
    """Demo different ways to initialize AetherMagic from configs"""
    
    print("=== AetherMagic Configuration Demo ===\n")
    
    # Method 1: Direct dictionary config
    print("1. Initialize from dictionary configs:")
    try:
        mqtt_magic = AetherMagicFactory.from_dict(MQTT_CONFIG)
        redis_magic = AetherMagicFactory.from_dict(REDIS_CONFIG)
        
        print(f"   ✅ MQTT: {mqtt_magic.config.protocol_type.value} on {mqtt_magic.config.host}:{mqtt_magic.config.port} (channel: {mqtt_magic.config.channel})")
        print(f"   ✅ Redis: {redis_magic.config.protocol_type.value} on {redis_magic.config.host}:{redis_magic.config.port} (channel: {redis_magic.config.channel})")
    except Exception as e:
        print(f"   ❌ Dictionary config failed: {e}")
    
    # Method 2: Environment-based config
    print("\n2. Initialize from environment functions:")
    try:
        mqtt_env_magic = AetherMagicFactory.from_dict(get_mqtt_config())
        redis_env_magic = AetherMagicFactory.from_dict(get_redis_config())
        
        print(f"   ✅ MQTT (env): {mqtt_env_magic.config.protocol_type.value} on {mqtt_env_magic.config.host}:{mqtt_env_magic.config.port}")
        print(f"   ✅ Redis (env): {redis_env_magic.config.protocol_type.value} on {redis_env_magic.config.host}:{redis_env_magic.config.port}")
    except Exception as e:
        print(f"   ❌ Environment config failed: {e}")
    
    # Method 3: Class-based config
    print("\n3. Initialize from config classes:")
    try:
        mqtt_class_magic = AetherMagicFactory.from_dict(MQTT_PROD.to_dict())
        redis_class_magic = AetherMagicFactory.from_dict(REDIS_PROD.to_dict())
        
        print(f"   ✅ MQTT (class): {mqtt_class_magic.config.protocol_type.value} on {mqtt_class_magic.config.host}:{mqtt_class_magic.config.port}")
        print(f"   ✅ Redis (class): {redis_class_magic.config.protocol_type.value} on {redis_class_magic.config.host}:{redis_class_magic.config.port}")
    except Exception as e:
        print(f"   ❌ Class config failed: {e}")
    
    # Method 4: Environment variables (set some examples)
    print("\n4. Initialize from environment variables:")
    os.environ.update({
        "AETHER_MQTT_PROTOCOL": "mqtt",
        "AETHER_MQTT_HOST": "mqtt.example.com", 
        "AETHER_MQTT_PORT": "1883",
        "AETHER_MQTT_CHANNEL": "mqtt_env",
        "AETHER_REDIS_PROTOCOL": "redis",
        "AETHER_REDIS_HOST": "redis.example.com",
        "AETHER_REDIS_PORT": "6379", 
        "AETHER_REDIS_CHANNEL": "redis_env"
    })
    
    try:
        # Create separate factories for different prefixes
        os.environ.update({
            "AETHER_PROTOCOL": "mqtt",
            "AETHER_HOST": "mqtt-from-env.com",
            "AETHER_CHANNEL": "mqtt_channel"
        })
        mqtt_env_factory = AetherMagicFactory.from_env("AETHER")
        print(f"   ✅ MQTT (env factory): {mqtt_env_factory.config.protocol_type.value} on {mqtt_env_factory.config.host} (channel: {mqtt_env_factory.config.channel})")
        
        os.environ.update({
            "REDIS_PROTOCOL": "redis", 
            "REDIS_HOST": "redis-from-env.com",
            "REDIS_CHANNEL": "redis_channel"
        })
        redis_env_factory = AetherMagicFactory.from_env("REDIS")
        print(f"   ✅ Redis (env factory): {redis_env_factory.config.protocol_type.value} on {redis_env_factory.config.host} (channel: {redis_env_factory.config.channel})")
        
    except Exception as e:
        print(f"   ❌ Environment factory failed: {e}")
    
    # Method 5: Show JSON config file example
    print("\n5. JSON config file structure:")
    print("   Create config.json with this structure:")
    print(f"   {json.dumps(CONFIG_TEMPLATE, indent=4)}")
    print("   Then use: AetherMagicFactory.from_json_file('config.json', 'mqtt')")
    
    # Method 6: Demonstrate multi-instance setup
    print("\n6. Multi-protocol service setup:")
    
    service_configs = {
        "mqtt_primary": {
            "protocol_type": "mqtt",
            "host": "primary-mqtt.service.com",
            "port": 1883,
            "channel": "mqtt_primary",
            "union": "production",
            "ssl": True,
            "username": "service_account",
            "password": "secret123"
        },
        "redis_cache": {
            "protocol_type": "redis", 
            "host": "cache-redis.service.com",
            "port": 6379,
            "channel": "redis_cache",
            "union": "production", 
            "password": "redis_secret",
            "use_streams": False
        },
        "redis_tasks": {
            "protocol_type": "redis",
            "host": "tasks-redis.service.com", 
            "port": 6380,
            "channel": "redis_tasks",
            "union": "production",
            "password": "redis_tasks_secret",
            "use_streams": True,
            "consumer_group": "task_workers"
        }
    }
    
    instances = {}
    for name, config in service_configs.items():
        try:
            instances[name] = AetherMagicFactory.from_dict(config)
            protocol = instances[name].config.protocol_type.value
            host = instances[name].config.host
            port = instances[name].config.port
            channel = instances[name].config.channel
            print(f"   ✅ {name}: {protocol} on {host}:{port} (channel: {channel})")
        except Exception as e:
            print(f"   ❌ {name}: {e}")
    
    print("\n=== Configuration Demo Complete ===")
    print("✅ Multiple ways to configure AetherMagic demonstrated")
    print("✅ Support for JSON/YAML files, environment variables, and dictionaries")
    print("✅ Factory pattern for consistent initialization") 
    print("✅ Multi-protocol service architecture ready")

if __name__ == '__main__':
    demo_config_initialization()