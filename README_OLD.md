# AetherMagic - Multi-Protocol Microservices Communication

AetherMagic now supports multiple communication protocols for microservices, providing a unified API for different transport mechanisms.

## Supported Protocols

### 1. MQTT (original)
- Lightweight protocol for IoT and microservices
- Shared subscriptions support for load balancing
- SSL/TLS encryption

### 2. Redis Pub/Sub + Streams
- **Pub/Sub**: Fast in-memory message delivery
- **Streams**: Reliable delivery with guarantees and consumer groups
- High performance

### 3. HTTP/WebSocket
- **HTTP**: REST API for reliable delivery
- **WebSocket**: Real-time communication
- Web interface compatibility

### 4. ZeroMQ
- High-performance messaging
- Various patterns: PUB/SUB, PUSH/PULL, REQ/REP
- Brokerless architecture

## Installation

```bash
pip install aethermagic

# For all protocols install additional dependencies:
pip install redis aiohttp websockets pyzmq
```

## Usage

### Quick Start with Different Protocols

```python
import asyncio
from aethermagic import AetherMagic, ProtocolType, AetherTask

# MQTT (original)
aether_mqtt = AetherMagic(
    protocol_type=ProtocolType.MQTT,
    host='localhost',
    port=1883
)

# Redis Pub/Sub
aether_redis = AetherMagic(
    protocol_type=ProtocolType.REDIS,
    host='localhost',
    port=6379
)

# Redis Streams (with reliable delivery)
aether_streams = AetherMagic(
    protocol_type=ProtocolType.REDIS,
    host='localhost',
    port=6379,
    use_streams=True,
    consumer_group='workers'
)

# HTTP/WebSocket
aether_http = AetherMagic(
    protocol_type=ProtocolType.HTTP,
    host='localhost',
    port=8080,
    mode='client'  # or 'server'
)

# ZeroMQ
aether_zmq = AetherMagic(
    protocol_type=ProtocolType.ZEROMQ,
    host='localhost',
    port=5555,
    pattern='pubsub'  # or 'pushpull', 'reqrep'
)
```

### Creating a Worker

```python
async def handle_task(ae_task, data):
    print(f"Processing: {data}")
    
    # Send intermediate status
    await ae_task.status(50)
    
    # Simulate work
    await asyncio.sleep(2)
    
    # Complete task
    await ae_task.complete(True, {"result": "success"})

# Create task
task = AetherTask(
    job='my_service',
    task='process_data', 
    context='production',
    on_perform=handle_task
)

# Register worker
await task.idle()

# Start main loop
await aether.main()
```

### Sending Tasks from Client

```python
async def on_status(ae_task, complete, succeed, progress, data):
    if complete:
        print(f"Task finished: {succeed}")
    else:
        print(f"Progress: {progress}%")

async def on_complete(ae_task, succeed, data):
    print(f"Result: {data}")

# Create client task
client_task = AetherTask(
    job='my_service',
    task='process_data',
    context='production',
    on_status=on_status,
    on_complete=on_complete
)

# Send task
await client_task.perform({
    "input_file": "/path/to/data.csv",
    "options": {"format": "json"}
})
```

## Protocol Selection Guide

### MQTT
**Use when:**
- Need IoT device compatibility
- Require lightweight protocol
- Have bandwidth constraints

### Redis Pub/Sub
**Use when:**
- Need maximum speed
- Already have Redis in infrastructure
- Message loss on failures is acceptable

### Redis Streams  
**Use when:**
- Need reliable message delivery
- Require load balancing between workers
- Message persistence is important

### HTTP/WebSocket
**Use when:**
- Need web application integration
- Require HTTP proxy/load balancer compatibility
- Need REST API for external systems

### ZeroMQ
**Use when:**
- Maximum performance is critical
- Don't want external broker dependencies
- Need specific communication patterns

## Examples

See `examples.py` for complete usage examples of each protocol:

```bash
# Run Redis example
python examples.py redis

# Run HTTP/WebSocket example  
python examples.py http

# Run ZeroMQ example
python examples.py zeromq

# Multi-protocol example
python examples.py multi
```

## Configuration

### Common Parameters
```python
config = ConnectionConfig(
    protocol_type=ProtocolType.REDIS,
    host='localhost',
    port=6379,
    ssl=False,
    username='user',
    password='pass',
    union='my_app',  # namespace for application
    timeout=30,
    keepalive=60
)
```

### Protocol-Specific Parameters

#### Redis Streams
```python
aether = AetherMagic(
    protocol_type=ProtocolType.REDIS,
    use_streams=True,
    consumer_group='workers',
    consumer_name='worker_1'
)
```

#### HTTP/WebSocket
```python
aether = AetherMagic(
    protocol_type=ProtocolType.HTTP,
    mode='server',  # or 'client'
    ssl=True
)
```

#### ZeroMQ
```python
aether = AetherMagic(
    protocol_type=ProtocolType.ZEROMQ,
    pattern='pushpull',  # 'pubsub', 'reqrep', 'all'
    server_mode=True
)
```

## Performance Comparison

| Protocol | Throughput | Latency | Reliability | Complexity |
|----------|------------|---------|-------------|------------|
| MQTT | Medium | Low | High | Low |
| Redis Pub/Sub | High | Very Low | Medium | Low |
| Redis Streams | High | Low | High | Medium |
| HTTP/WebSocket | Medium | Medium | High | Medium |
| ZeroMQ | Very High | Very Low | Medium | High |

## Backward Compatibility

Existing MQTT code continues to work without changes:

```python
# Old code
from aethermagic import AetherMagic

aether = AetherMagic(server="localhost", port=1883)
```

The new API is fully compatible and adds additional capabilities.