"""
Configuration examples for AetherMagic with multiple protocols
"""

# Example 1: Simple dictionary configs
MQTT_CONFIG = {
    "protocol_type": "mqtt",
    "host": "localhost",
    "port": 1883,
    "ssl": False,
    "username": "mqtt_user",
    "password": "mqtt_pass",
    "union": "production",
    "channel": "mqtt",
    "keepalive": 60
}

REDIS_CONFIG = {
    "protocol_type": "redis",
    "host": "localhost", 
    "port": 6379,
    "ssl": False,
    "username": "",
    "password": "redis_pass",
    "union": "production",
    "channel": "redis",
    "use_streams": False  # Extra parameter for Redis
}

# Example 2: Environment-based configs
import os

def get_mqtt_config():
    return {
        "protocol_type": "mqtt",
        "host": os.getenv("MQTT_HOST", "localhost"),
        "port": int(os.getenv("MQTT_PORT", "1883")),
        "ssl": os.getenv("MQTT_SSL", "false").lower() == "true",
        "username": os.getenv("MQTT_USER", ""),
        "password": os.getenv("MQTT_PASS", ""),
        "union": os.getenv("AETHER_UNION", "default"),
        "channel": "mqtt",
        "keepalive": int(os.getenv("MQTT_KEEPALIVE", "60"))
    }

def get_redis_config():
    return {
        "protocol_type": "redis",
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": int(os.getenv("REDIS_PORT", "6379")),
        "ssl": os.getenv("REDIS_SSL", "false").lower() == "true",
        "username": os.getenv("REDIS_USER", ""),
        "password": os.getenv("REDIS_PASS", ""),
        "union": os.getenv("AETHER_UNION", "default"),
        "channel": "redis",
        "use_streams": os.getenv("REDIS_USE_STREAMS", "false").lower() == "true",
        "consumer_group": os.getenv("REDIS_CONSUMER_GROUP", "workers")
    }

# Example 3: JSON/YAML config file structure
CONFIG_TEMPLATE = {
    "aether_services": {
        "mqtt": {
            "protocol_type": "mqtt",
            "connection": {
                "host": "mqtt.example.com",
                "port": 1883,
                "ssl": False,
                "username": "service_user",
                "password": "secret_password"
            },
            "settings": {
                "union": "production",
                "channel": "mqtt",
                "keepalive": 60,
                "clean_session": True
            }
        },
        "redis": {
            "protocol_type": "redis", 
            "connection": {
                "host": "redis.example.com",
                "port": 6379,
                "ssl": True,
                "username": "",
                "password": "redis_secret"
            },
            "settings": {
                "union": "production",
                "channel": "redis",
                "use_streams": True,
                "consumer_group": "microservice_workers",
                "max_connections": 10
            }
        }
    }
}

# Example 4: Class-based config
class AetherConfig:
    def __init__(self, protocol_type, host, port, channel, **kwargs):
        self.protocol_type = protocol_type
        self.host = host
        self.port = port
        self.channel = channel
        self.kwargs = kwargs
    
    def to_dict(self):
        return {
            "protocol_type": self.protocol_type,
            "host": self.host,
            "port": self.port,
            "channel": self.channel,
            **self.kwargs
        }

# Predefined configs
MQTT_PROD = AetherConfig(
    protocol_type="mqtt",
    host="prod-mqtt.company.com", 
    port=1883,
    channel="mqtt",
    ssl=True,
    username="prod_service",
    password="prod_password",
    union="production"
)

REDIS_PROD = AetherConfig(
    protocol_type="redis",
    host="prod-redis.company.com",
    port=6380,
    channel="redis", 
    ssl=True,
    password="redis_prod_password",
    union="production",
    use_streams=True,
    consumer_group="prod_workers"
)