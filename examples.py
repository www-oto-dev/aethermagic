"""
AetherMagic usage examples with different protocols
"""

import asyncio
from aethermagic import AetherMagic, ProtocolType, ConnectionConfig


async def example_mqtt():
    """Example usage with MQTT (original protocol)"""
    print("=== MQTT Protocol Example ===")
    
    aether = AetherMagic(
        protocol_type=ProtocolType.MQTT,
        host='localhost',
        port=1883,
        union='example'
    )
    
    # Task handler
    async def handle_task(ae_task, data):
        print(f"Processing task: {data}")
        await ae_task.status(50)
        await asyncio.sleep(2)  # Work simulation
        await ae_task.complete(True, {"result": "success"})
    
    from aethermagic import AetherTask
    
    # Create task
    task = AetherTask(
        job='example',
        task='process_data',
        context='test',
        on_perform=handle_task
    )
    
    # Start worker
    await task.idle()
    
    # Start main loop
    await aether.main()


async def example_redis():
    """Example usage with Redis Pub/Sub"""
    print("=== Redis Protocol Example ===")
    
    aether = AetherMagic(
        protocol_type=ProtocolType.REDIS,
        host='localhost',
        port=6379,
        union='example'
    )
    
    async def handle_task(ae_task, data):
        print(f"Redis: Processing task: {data}")
        await ae_task.status(25)
        await asyncio.sleep(1)
        await ae_task.status(75)
        await asyncio.sleep(1)
        await ae_task.complete(True, {"result": "redis_success"})
    
    from aethermagic import AetherTask
    
    task = AetherTask(
        job='example',
        task='redis_task',
        context='test',
        on_perform=handle_task
    )
    
    await task.idle()
    await aether.main()


async def example_redis_streams():
    """Example usage with Redis Streams for reliable delivery"""
    print("=== Redis Streams Protocol Example ===")
    
    aether = AetherMagic(
        protocol_type=ProtocolType.REDIS,
        host='localhost',
        port=6379,
        union='example',
        use_streams=True,  # Use Redis Streams
        consumer_group='workers',
        consumer_name='worker_1'
    )
    
    async def handle_reliable_task(ae_task, data):
        print(f"Redis Streams: Processing reliable task: {data}")
        await ae_task.status(33)
        await asyncio.sleep(0.5)
        await ae_task.status(66)
        await asyncio.sleep(0.5) 
        await ae_task.complete(True, {"result": "reliable_success"})
    
    from aethermagic import AetherTask
    
    task = AetherTask(
        job='example',
        task='reliable_task',
        context='production',
        on_perform=handle_reliable_task
    )
    
    await task.idle()
    await aether.main()


async def example_http_websocket():
    """Example usage with HTTP/WebSocket"""
    print("=== HTTP/WebSocket Protocol Example ===")
    
    # Server
    server = AetherMagic(
        protocol_type=ProtocolType.HTTP,
        host='localhost',
        port=8080,
        union='example',
        mode='server'
    )
    
    # Client
    client = AetherMagic(
        protocol_type=ProtocolType.HTTP,
        host='localhost', 
        port=8080,
        union='example',
        mode='client'
    )
    
    async def handle_http_task(ae_task, data):
        print(f"HTTP: Processing task: {data}")
        await ae_task.status(40)
        await asyncio.sleep(1.5)
        await ae_task.status(80)
        await asyncio.sleep(0.5)
        await ae_task.complete(True, {"result": "http_success"})
    
    from aethermagic import AetherTask
    
    # Client task
    task = AetherTask(
        job='example',
        task='http_task',
        context='web',
        on_perform=handle_http_task
    )
    
    # Start server and client
    asyncio.create_task(server.main())
    await asyncio.sleep(1)  # Give server time to start
    
    await task.idle()
    await client.main()


async def example_zeromq():
    """Example usage with ZeroMQ"""
    print("=== ZeroMQ Protocol Example ===")
    
    aether = AetherMagic(
        protocol_type=ProtocolType.ZEROMQ,
        host='localhost',
        port=5555,
        union='example',
        pattern='pubsub',  # Can use 'pushpull', 'reqrep'
        server_mode=False
    )
    
    async def handle_zmq_task(ae_task, data):
        print(f"ZeroMQ: Processing high-performance task: {data}")
        await ae_task.status(20)
        await asyncio.sleep(0.3)
        await ae_task.status(60)
        await asyncio.sleep(0.3)
        await ae_task.status(90)
        await asyncio.sleep(0.2)
        await ae_task.complete(True, {"result": "zmq_success", "speed": "high"})
    
    from aethermagic import AetherTask
    
    task = AetherTask(
        job='example',
        task='performance_task',
        context='compute',
        on_perform=handle_zmq_task
    )
    
    await task.idle()
    await aether.main()


async def example_multi_protocol():
    """Example usage with multiple protocols simultaneously"""
    print("=== Multi-Protocol Example ===")
    
    # Create multiple instances with different protocols
    protocols = [
        (ProtocolType.REDIS, 6379, "redis_worker"),
        (ProtocolType.ZEROMQ, 5555, "zmq_worker"),
        (ProtocolType.HTTP, 8080, "http_worker")
    ]
    
    tasks = []
    
    for protocol_type, port, worker_name in protocols:
        aether = AetherMagic(
            protocol_type=protocol_type,
            host='localhost',
            port=port,
            union='multi_example'
        )
        
        async def handle_multi_task(ae_task, data, worker=worker_name):
            print(f"{worker}: Processing task: {data}")
            await ae_task.status(50)
            await asyncio.sleep(1)
            await ae_task.complete(True, {"worker": worker, "result": "success"})
        
        from aethermagic import AetherTask
        
        task = AetherTask(
            job='multi',
            task='distributed_task',
            context='test',
            on_perform=handle_multi_task
        )
        
        # Run each protocol in separate task
        async def run_protocol():
            await task.idle()
            await aether.main()
        
        tasks.append(asyncio.create_task(run_protocol()))
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)


async def client_example():
    """Example client that sends tasks"""
    print("=== Client Example ===")
    
    client = AetherMagic(
        protocol_type=ProtocolType.REDIS,  # Can change protocol
        host='localhost',
        port=6379,
        union='example'
    )
    
    # Status and completion handlers
    async def on_status(ae_task, complete, succeed, progress, data):
        if not complete:
            print(f"Task progress: {progress}%")
        else:
            print(f"Task completed: {'Success' if succeed else 'Failed'}")
    
    async def on_complete(ae_task, succeed, data):
        print(f"Final result: {data}")
    
    from aethermagic import AetherTask
    
    # Create and send task
    task = AetherTask(
        job='example',
        task='process_data',
        context='test',
        on_status=on_status,
        on_complete=on_complete
    )
    
    # Send task
    await task.perform({
        "input": "test_data",
        "params": {"timeout": 30}
    })
    
    # Start client
    await client.main()


if __name__ == "__main__":
    import sys
    
    examples = {
        'mqtt': example_mqtt,
        'redis': example_redis,
        'redis_streams': example_redis_streams,
        'http': example_http_websocket,
        'zeromq': example_zeromq,
        'multi': example_multi_protocol,
        'client': client_example
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in examples:
        example = examples[sys.argv[1]]
    else:
        print("Available examples:")
        for name in examples.keys():
            print(f"  python examples.py {name}")
        sys.exit(1)
    
    # Run selected example
    asyncio.run(example())