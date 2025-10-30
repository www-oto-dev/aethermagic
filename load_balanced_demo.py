#!/usr/bin/env python3
"""
AetherMagic Load Balanced Task Demo
Demonstrates single-delivery task distribution across multiple workers
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aethermagic import AetherMessage, AetherMagic
from aethermagic.protocols.redis_protocol import RedisLoadBalancedProtocol
from aethermagic.protocols import ConnectionConfig, ProtocolType


async def worker_task_handler(worker_id: str, message: AetherMessage):
    """Task handler for worker"""
    print(f"[Worker {worker_id}] Received task: {message.data}")
    
    # Simulate work
    await asyncio.sleep(1)
    
    print(f"[Worker {worker_id}] Completed task: {message.data}")


async def run_load_balanced_demo():
    """Run load balanced task distribution demo"""
    print("=== AetherMagic Load Balanced Task Demo ===")
    
    # Create Redis load balanced protocol
    config = ConnectionConfig(
        host="localhost",
        port=6379,
        union="loadtest"
    )
    
    # Create multiple workers
    workers = []
    for i in range(3):
        worker = RedisLoadBalancedProtocol(config, consumer_id=f"worker_{i}")
        await worker.connect()
        
        # Subscribe to load-balanced tasks
        await worker.subscribe_to_tasks(
            job="processing",
            task="compute", 
            context="demo",
            callback=lambda msg, wid=f"worker_{i}": asyncio.create_task(
                worker_task_handler(wid, msg)
            )
        )
        
        workers.append(worker)
        print(f"Started worker_{i}")
    
    # Create task publisher
    publisher = RedisLoadBalancedProtocol(config, consumer_id="publisher")
    await publisher.connect()
    
    print("\nPublishing 10 tasks...")
    
    # Publish tasks - each should go to only one worker
    for i in range(10):
        task_message = AetherMessage(
            action="perform",
            data=f"Task #{i+1}",
            source="demo_publisher"
        )
        
        success = await publisher.publish_task(
            job="processing",
            task="compute",
            context="demo", 
            message=task_message,
            shared=True  # Enable load balancing
        )
        
        if success:
            print(f"Published task #{i+1}")
        else:
            print(f"Failed to publish task #{i+1}")
    
    # Let workers process tasks
    print("\nLet workers process tasks for 5 seconds...")
    await asyncio.sleep(5)
    
    # Cleanup
    print("\nCleaning up...")
    for i, worker in enumerate(workers):
        await worker.unsubscribe_from_tasks("processing", "compute", "demo")
        await worker.disconnect()
        print(f"Stopped worker_{i}")
    
    await publisher.disconnect()
    print("Demo completed!")


async def run_multi_protocol_demo():
    """Demo using MultiProtocolAetherMagic with load balancing"""
    print("\n=== Multi-Protocol Load Balancing Demo ===")
    
    # Create AetherMagic instances with different protocols
    configs = [
        ("redis", "localhost", 6379),
        ("zeromq", "localhost", 5555),
        ("websocket", "localhost", 8080)
    ]
    
    workers = {}
    
    # Start workers for each protocol
    for proto_name, host, port in configs:
        print(f"\nStarting {proto_name} worker...")
        
        config = ConnectionConfig(
            host=host,
            port=port,
            union="multitest"
        )
        
        try:
            if proto_name == "redis":
                protocol_type = ProtocolType.REDIS
            elif proto_name == "zeromq":
                protocol_type = ProtocolType.ZEROMQ
            elif proto_name == "websocket":
                protocol_type = ProtocolType.WEBSOCKET
            
            worker = AetherMagic(protocol_type=protocol_type, host=host, port=port, union="multitest")
            await worker.connect()
            
            # Subscribe with shared subscription for load balancing
            await worker.add_task(
                job="multitest",
                task="work",
                context="demo",
                callback=lambda msg, proto=proto_name: print(
                    f"[{proto} Worker] Processed: {msg.data}"
                ),
                shared=True  # Enable load balancing
            )
            
            workers[proto_name] = worker
            print(f"{proto_name} worker ready")
            
        except Exception as e:
            print(f"Failed to start {proto_name} worker: {e}")
    
    # Publish tasks to each protocol
    print(f"\nPublishing tasks to {len(workers)} protocols...")
    
    for proto_name, worker in workers.items():
        for i in range(3):
            task_message = AetherMessage(
                action="perform",
                data=f"{proto_name.upper()} Task #{i+1}",
                source="multi_demo"
            )
            
            await worker.perform_task(
                job="multitest",
                task="work", 
                context="demo",
                data=task_message.data,
                shared=True  # Load balanced
            )
    
    # Let workers process
    await asyncio.sleep(3)
    
    # Cleanup
    for proto_name, worker in workers.items():
        await worker.disconnect()
        print(f"Stopped {proto_name} worker")


async def main():
    """Run all demos"""
    try:
        # Redis load balanced demo
        await run_load_balanced_demo()
        
        # Multi-protocol demo
        await run_multi_protocol_demo()
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())