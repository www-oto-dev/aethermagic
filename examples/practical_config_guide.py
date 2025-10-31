#!/usr/bin/env python3
"""
Practical AetherMagic Configuration Guide

This shows real-world patterns for configuring and initializing 
multiple AetherMagic instances in a microservice.
"""

import sys
import os
import json

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

# Simple config structures
CONFIGS = {
    # MQTT Configuration
    "mqtt": {
        "protocol_type": "mqtt",
        "host": "localhost",
        "port": 1883,
        "ssl": False,
        "username": "mqtt_user", 
        "password": "mqtt_pass",
        "union": "production",
        "channel": "mqtt"
    },
    
    # Redis Configuration  
    "redis": {
        "protocol_type": "redis",
        "host": "localhost",
        "port": 6379,
        "ssl": False,
        "username": "",
        "password": "redis_pass", 
        "union": "production",
        "channel": "redis",
        # Redis-specific options
        "use_streams": False
    }
}

def init_aether_services():
    """Initialize AetherMagic instances from configs"""
    
    print("=== Initializing AetherMagic Services ===\n")
    
    # This is the import you would use in real code:
    # from aethermagic import AetherMagic, AetherTask
    
    services = {}
    
    for name, config in CONFIGS.items():
        print(f"Configuring {name.upper()} service:")
        print(f"  Protocol: {config['protocol_type']}")
        print(f"  Host: {config['host']}:{config['port']}")
        print(f"  Channel: {config['channel']}")
        print(f"  Union: {config['union']}")
        
        # Real initialization would be:
        # services[name] = AetherMagic(**config)
        
        print(f"  ✅ {name.upper()} service configured\n")
    
    return services

def example_usage():
    """Show how to use configured services"""
    
    print("=== Usage Examples ===\n")
    
    print("1. Creating tasks for specific channels:")
    print("""
    # MQTT task
    mqtt_task = AetherTask(
        job='user_processing',
        task='send_notification', 
        context='email',
        channel='mqtt'  # Uses MQTT AetherMagic instance
    )
    
    # Redis task  
    redis_task = AetherTask(
        job='user_processing',
        task='cache_result',
        context='user_data', 
        channel='redis'  # Uses Redis AetherMagic instance
    )
    """)
    
    print("\n2. Environment-based configuration:")
    print("""
    # Set environment variables:
    export MQTT_HOST=prod-mqtt.company.com
    export MQTT_PORT=1883
    export MQTT_USER=prod_service
    export MQTT_PASS=secret123
    
    export REDIS_HOST=prod-redis.company.com  
    export REDIS_PORT=6379
    export REDIS_PASS=redis_secret
    
    # Then in code:
    mqtt_config = {
        'protocol_type': 'mqtt',
        'host': os.getenv('MQTT_HOST', 'localhost'),
        'port': int(os.getenv('MQTT_PORT', '1883')),
        'username': os.getenv('MQTT_USER', ''),
        'password': os.getenv('MQTT_PASS', ''),
        'channel': 'mqtt',
        'union': 'production'
    }
    mqtt_magic = AetherMagic(**mqtt_config)
    """)
    
    print("\n3. JSON config file approach:")
    
    config_example = {
        "services": {
            "messaging": {
                "protocol_type": "mqtt",
                "host": "mqtt-broker.internal",
                "port": 1883,
                "channel": "messaging",
                "union": "production",
                "ssl": True,
                "username": "service_account",
                "password": "${MQTT_PASSWORD}"
            },
            "caching": {
                "protocol_type": "redis", 
                "host": "redis-cache.internal",
                "port": 6379,
                "channel": "caching",
                "union": "production",
                "password": "${REDIS_PASSWORD}",
                "use_streams": False
            },
            "tasks": {
                "protocol_type": "redis",
                "host": "redis-tasks.internal", 
                "port": 6380,
                "channel": "tasks",
                "union": "production", 
                "password": "${REDIS_TASKS_PASSWORD}",
                "use_streams": True,
                "consumer_group": "worker_pool"
            }
        }
    }
    
    print("   Save this as services.json:")
    print(f"   {json.dumps(config_example, indent=4)}")
    
    print("""
    # Load and use:
    with open('services.json', 'r') as f:
        config = json.load(f)
    
    services = {}
    for name, service_config in config['services'].items():
        # Substitute environment variables
        for key, value in service_config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                env_var = value[2:-1]  # Remove ${ and }
                service_config[key] = os.getenv(env_var)
        
        services[name] = AetherMagic(**service_config)
    """)
    
    print("\n4. Service factory pattern:")
    print("""
    class ServiceManager:
        def __init__(self, config_file='services.json'):
            self.services = {}
            self.load_config(config_file)
        
        def load_config(self, config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            for name, service_config in config['services'].items():
                self.services[name] = AetherMagic(**service_config)
        
        def get_service(self, name):
            return self.services[name]
        
        def create_task(self, service_name, job, task, context='default'):
            service = self.services[service_name]
            return AetherTask(
                job=job,
                task=task, 
                context=context,
                channel=service.config.channel
            )
    
    # Usage:
    manager = ServiceManager()
    
    # Get services
    mqtt_service = manager.get_service('messaging')
    redis_service = manager.get_service('caching')
    
    # Create tasks
    notification_task = manager.create_task('messaging', 'notifications', 'send_email')
    cache_task = manager.create_task('caching', 'user_data', 'store_session')
    """)

def main():
    """Main demo function"""
    
    print("🚀 AetherMagic Multi-Protocol Configuration Guide\n")
    
    # Show initialization
    init_aether_services()
    
    # Show usage patterns
    example_usage()
    
    print("\n" + "="*50)
    print("📋 Configuration Checklist:")
    print("✅ Define protocol configs (MQTT, Redis, etc.)")
    print("✅ Set unique channels for each service")
    print("✅ Use environment variables for secrets")
    print("✅ Create AetherMagic instances with configs") 
    print("✅ Create AetherTask with matching channels")
    print("✅ Use factory patterns for management")
    print("\n🎯 Result: Multiple protocols in one microservice!")

if __name__ == '__main__':
    main()