# AetherMagic - Multi-Protocol Microservices Communication

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AetherMagic is a powerful multi-protocol communication library for microservices, providing a unified API for different transport mechanisms including MQTT, Redis, HTTP/WebSocket, and ZeroMQ.

## Supported Protocols

### 1. MQTT (original) - **Best for Task Distribution**
- Lightweight protocol for IoT and microservices
- **Shared subscriptions** for automatic load balancing
- Built-in task distribution among multiple workers
- SSL/TLS encryption

### 2. Redis Pub/Sub + Streams
- **Pub/Sub**: Fast in-memory message delivery
- **Streams**: Reliable delivery with load-balanced consumer groups
- High performance, atomic operations

### 3. WebSocket
- Real-time bidirectional communication
- Built-in load balancing with random client selection
- Web interface compatibility

### 4. ZeroMQ
- High-performance messaging with natural load balancing
- PUSH/PULL pattern for automatic task distribution
- Brokerless architecture

## Installation

### Basic Installation
```bash
pip install aethermagic
```

### Protocol-Specific Installation
Install only the protocols you need:

```bash
# For MQTT support
pip install aethermagic[mqtt]

# For Redis support  
pip install aethermagic[redis]

# For WebSocket support
pip install aethermagic[websocket]

# For ZeroMQ support
pip install aethermagic[zeromq]

# For RabbitMQ support
pip install aethermagic[rabbitmq]

# Install all protocols
pip install aethermagic[all]
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

## Task Distribution & Load Balancing

AetherMagic automatically distributes tasks among multiple workers for all protocols:

### MQTT with Shared Subscriptions
```python
# Multiple workers subscribe to shared topic
# $share/union_job_workgroup/union/job/task/context/+/perform
await aether.listen('image-process', 'resize', 'batch1', 'perform', 'workers', handle_task)
```

### Redis with Consumer Groups  
```python
# Atomic LPUSH/BRPOP operations ensure single delivery
await aether.listen('image-process', 'resize', 'batch1', 'perform', 'workers', handle_task)
```

### WebSocket with Random Selection
```python
# Tasks distributed randomly among connected clients
await aether.listen('image-process', 'resize', 'batch1', 'perform', 'workers', handle_task)  
```

### ZeroMQ PUSH/PULL Pattern
```python  
# Natural load balancing with PUSH/PULL sockets
await aether.listen('image-process', 'resize', 'batch1', 'perform', 'workers', handle_task)
```

**Key Benefits:**
- 🔄 **Automatic load balancing** - tasks distributed among available workers
- 🚫 **No duplicate processing** - each task handled by exactly one worker  
- 📈 **Horizontal scaling** - add more workers to increase capacity
- 🛡️ **Fault tolerance** - failed workers don't block other workers

See [TASK_DISTRIBUTION.md](TASK_DISTRIBUTION.md) for detailed examples.

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

## Load Balancing Support

AetherMagic now supports load-balanced task distribution to ensure each task is processed by only one worker:

### Protocol-Specific Load Balancing

#### Redis Protocol
- **RedisLoadBalancedProtocol**: Uses Redis lists (LPUSH/BRPOP) for atomic task distribution
- Each task goes to exactly one available worker
- FIFO processing with blocking pop operations

```python
from aethermagic.protocols.redis_protocol import RedisLoadBalancedProtocol

worker = RedisLoadBalancedProtocol(config, consumer_id="worker_1")
await worker.subscribe_to_tasks("job", "task", "context", callback)
```

#### MQTT Protocol  
- Uses shared subscriptions with `$share` prefix
- Broker distributes messages among group subscribers
- Built-in load balancing at protocol level

#### ZeroMQ Protocol
- Uses PUSH/PULL socket pattern for task distribution  
- Round-robin delivery to connected workers
- No message duplication - perfect for task distribution

#### WebSocket Protocol
- Implements random selection among subscribed clients
- Tasks with 'shared:' or 'tasks:' prefixes are load balanced
- Single delivery guaranteed per task

### Multi-Protocol Load Balancing API

Use the new convenience methods for load-balanced task processing:

```python
from aethermagic import AetherMagic, ProtocolType

# Create workers  
worker = AetherMagic(protocol_type=ProtocolType.REDIS, host="localhost", port=6379)
await worker.connect()

# Add load-balanced task handler
await worker.add_task(
    job="processing",
    task="compute", 
    context="demo",
    callback=task_handler,
    shared=True  # Enable load balancing
)

# Publish load-balanced tasks
await worker.perform_task(
    job="processing",
    task="compute",
    context="demo", 
    data={"work": "data"},
    shared=True  # Only one worker will receive this
)
```

### Single Delivery Guarantees

- **Redis**: Atomic LPUSH/BRPOP operations ensure single delivery
- **MQTT**: Broker's shared subscription handles distribution  

## Multi-Protocol Setup (Channel Support)

AetherMagic supports running multiple protocols simultaneously using channel isolation:

```python
import asyncio
from aethermagic import AetherMagic, AetherTask

async def multi_protocol_service():
    # MQTT for general messaging
    mqtt_service = AetherMagic(
        protocol_type='mqtt',
        host='mqtt.example.com',
        port=8883,
        ssl=True,
        union='production',
        channel='messaging'  # 🔥 Channel identifier
    )
    
    # Redis for caching and AI tasks
    redis_service = AetherMagic(
        protocol_type='redis', 
        host='redis.example.com',
        port=6379,
        ssl=True,
        union='production',
        channel='caching'  # 🔥 Different channel
    )
    
    # Start both services
    mqtt_task = asyncio.create_task(mqtt_service.main())
    redis_task = asyncio.create_task(redis_service.main())
    
    # Create tasks for different channels
    mqtt_task = AetherTask(
        job='notifications',
        task='send_email',
        channel='messaging'  # Uses MQTT
    )
    
    redis_task = AetherTask(
        job='ai',
        task='generate_image', 
        channel='caching'  # Uses Redis
    )
    
    # Execute tasks
    await mqtt_task.perform({'email': 'user@example.com'})
    await redis_task.perform({'prompt': 'sunset landscape'})

# Run the service
asyncio.run(multi_protocol_service())
```

## Dependencies

AetherMagic automatically installs protocol-specific dependencies when you install the optional packages:

- **MQTT**: `asyncio-mqtt`, `paho-mqtt`, `aiomqtt`
- **Redis**: `redis[hiredis]` (includes high-performance hiredis parser)
- **WebSocket**: `aiohttp`, `websockets`
- **ZeroMQ**: `pyzmq`
- **RabbitMQ**: `aio-pika`
- **ZeroMQ**: PUSH/PULL pattern is inherently load-balanced
- **WebSocket**: Random selection with connection tracking

All protocols now support the `shared=True` parameter for load-balanced task distribution.

See `load_balanced_demo.py` for complete working examples.