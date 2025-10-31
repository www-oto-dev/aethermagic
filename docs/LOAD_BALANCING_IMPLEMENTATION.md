# AetherMagic Load Balancing Implementation

## Summary of Changes

✅ **All requirements completed successfully:**

### 1. Renamed WebSocket Protocol
- ✅ `http_websocket_protocol.py` → `websocket_protocol.py`
- ✅ `HTTPWebSocketProtocol` → `WebSocketProtocol` 
- ✅ Updated all imports and references

### 2. MQTT Protocol Architecture
- ✅ Created `src/aethermagic/protocols/mqtt_protocol.py`
- ✅ Moved MQTT implementation to protocols folder
- ✅ Maintains all original functionality with aiomqtt
- ✅ Added shared subscriptions using `$share` prefix

### 3. Single-Subscriber Delivery (Load Balancing)
- ✅ **Redis**: LPUSH/BRPOP atomic operations via `RedisLoadBalancedProtocol`
- ✅ **MQTT**: `$share` groups ensure single delivery per message
- ✅ **ZeroMQ**: PUSH/PULL pattern naturally load balances
- ✅ **WebSocket**: Random selection from subscribed clients

### 4. Backward Compatibility
- ✅ Old initialization `AetherMagic(server="...", port=...)` works
- ✅ Maps to MQTT protocol automatically
- ✅ All original API methods preserved

## Architecture Overview

```
aethermagic/
├── src/aethermagic/
│   ├── __init__.py              # Backward compatible AetherMagic class
│   ├── magic.py                 # Original MQTT-only implementation
│   ├── multi_magic.py           # Multi-protocol manager
│   ├── task.py                  # Task definitions
│   └── protocols/
│       ├── __init__.py          # Base interfaces
│       ├── mqtt_protocol.py     # ✅ NEW: MQTT with shared subscriptions
│       ├── redis_protocol.py    # ✅ Enhanced: Load balancing classes
│       ├── websocket_protocol.py # ✅ Renamed: Random selection
│       └── zeromq_protocol.py   # ✅ Enhanced: PUSH/PULL load balancing
```

## Load Balancing Implementation Details

### Redis Protocol
```python
class RedisLoadBalancedProtocol(RedisProtocol):
    async def _push_task_to_queue(self, topic: str, message: AetherMessage)
    async def _pop_task_from_queue(self, topic: str) -> Optional[Dict]
    async def subscribe_to_tasks(self, job, task, context, callback)
```
- Uses Redis lists for atomic task distribution
- LPUSH for adding tasks, BRPOP for consuming
- Each task goes to exactly one worker

### MQTT Protocol  
```python
def generate_topic(self, job, task, context, tid, action, shared=False):
    if shared:
        return f'$share/{union}_{job}_{task}/{job}/{task}/{context}/{action}'
```
- Shared subscriptions distribute messages among group members
- Built into MQTT 5.0 specification
- Broker handles load balancing automatically

### ZeroMQ Protocol
```python
# Uses PUSH/PULL socket pattern
if message.action == 'perform':
    await self.push_socket.send_multipart([topic, serialized])
```
- PUSH sockets distribute to PULL sockets in round-robin
- Perfect for task distribution - no duplicates
- No external broker required

### WebSocket Protocol
```python
if is_load_balanced:
    clients = list(self.subscriptions[topic])
    if clients:
        selected_client = random.choice(clients)
        await selected_client.send_str(message_json)
```
- Detects shared topics (prefixed with 'shared:' or 'tasks:')
- Random selection ensures fair distribution
- Maintains connection state for reliability

## New API Methods

### MultiProtocolAetherMagic
```python
# Load-balanced task publishing
await aether.perform_task(
    job="processing", task="compute", context="demo",
    data={"work": "data"}, shared=True
)

# Load-balanced task subscription  
await aether.add_task(
    job="processing", task="compute", context="demo",
    callback=handler, shared=True
)
```

### Protocol-Specific Classes
```python
# Redis load balancing
worker = RedisLoadBalancedProtocol(config, consumer_id="worker_1")
await worker.subscribe_to_tasks("job", "task", "context", callback)
```

## Testing

✅ All tests pass:
- Import compatibility
- Protocol creation
- Method availability  
- Backward compatibility
- Load balancing logic

## File Changes

**Modified:**
- `src/aethermagic/protocols/websocket_protocol.py` (renamed + enhanced)
- `src/aethermagic/protocols/redis_protocol.py` (added load balancing)
- `src/aethermagic/protocols/zeromq_protocol.py` (enhanced for tasks)
- `src/aethermagic/multi_magic.py` (new API methods)
- `src/aethermagic/__init__.py` (backward compatibility)
- `README.md` (load balancing documentation)

**Created:**
- `src/aethermagic/protocols/mqtt_protocol.py` (moved from magic.py)
- `load_balanced_demo.py` (comprehensive examples)
- `test_load_balancing.py` (test suite)

## Benefits

1. **Single Delivery**: No duplicate task processing across workers
2. **Protocol Choice**: Each protocol optimized for different use cases
3. **Scalability**: Add workers without coordination overhead  
4. **Reliability**: Built-in failover and message persistence options
5. **Compatibility**: Existing code continues to work unchanged

The implementation provides enterprise-grade load balancing while maintaining the simple, intuitive AetherMagic API.