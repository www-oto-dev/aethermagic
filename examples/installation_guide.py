#!/usr/bin/env python3
"""
Installation Examples: Different Ways to Install AetherMagic

This example shows how to install AetherMagic with different protocol support.
"""

print("""
AetherMagic Installation Guide
=============================

1. Basic Installation (core only):
   pip install aethermagic

2. Protocol-Specific Installation:
   pip install aethermagic[mqtt]      # MQTT support
   pip install aethermagic[redis]     # Redis support  
   pip install aethermagic[websocket] # WebSocket support
   pip install aethermagic[zeromq]    # ZeroMQ support
   pip install aethermagic[rabbitmq]  # RabbitMQ support

3. Multiple Protocols:
   pip install aethermagic[mqtt,redis]        # MQTT + Redis
   pip install aethermagic[mqtt,redis,websocket] # MQTT + Redis + WebSocket

4. All Protocols:
   pip install aethermagic[all]

Dependencies Included:
======================

MQTT Package:
- asyncio-mqtt>=0.16.0
- paho-mqtt>=2.1.0

Redis Package:  
- redis[hiredis]>=4.0.0 (includes high-performance hiredis parser)

WebSocket Package:
- aiohttp>=3.8.0
- websockets>=10.0

ZeroMQ Package:
- pyzmq>=24.0.0

RabbitMQ Package:
- aio-pika>=8.0.0

Usage Example:
==============
""")

# Example usage after installation
import asyncio

try:
    from aethermagic import AetherMagic, AetherTask
    print("✅ AetherMagic imported successfully!")
    
    # Test creation of different protocols
    protocols = []
    
    try:
        mqtt = AetherMagic(protocol_type='mqtt', host='localhost', channel='test-mqtt')
        protocols.append("MQTT")
    except ImportError as e:
        print(f"❌ MQTT not available: {e}")
    
    try:
        redis = AetherMagic(protocol_type='redis', host='localhost', channel='test-redis') 
        protocols.append("Redis")
    except ImportError as e:
        print(f"❌ Redis not available: {e}")
        
    try:
        ws = AetherMagic(protocol_type='websocket', host='localhost', channel='test-ws')
        protocols.append("WebSocket") 
    except ImportError as e:
        print(f"❌ WebSocket not available: {e}")
        
    try:
        zmq = AetherMagic(protocol_type='zeromq', host='localhost', channel='test-zmq')
        protocols.append("ZeroMQ")
    except ImportError as e:
        print(f"❌ ZeroMQ not available: {e}")
        
    print(f"\n✅ Available protocols: {', '.join(protocols)}")
    print(f"🎉 You can use {len(protocols)} protocol(s) with this installation!")

except ImportError as e:
    print(f"❌ AetherMagic not available: {e}")
    print("💡 Install with: pip install aethermagic[all]")