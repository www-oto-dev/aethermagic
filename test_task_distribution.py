#!/usr/bin/env python3
"""
Test task distribution with shared MQTT subscriptions
"""

import asyncio
import json
from src.aethermagic.magic import AetherMagic
from src.aethermagic.protocols import ConnectionConfig, ProtocolType

async def test_task_distribution():
    """Test that tasks are distributed among multiple workers using shared subscriptions"""
    
    # Configuration for MQTT
    config = ConnectionConfig(
        ProtocolType.MQTT, 
        'localhost',  # Assuming local MQTT broker
        1883, 
        union='test-union'
    )
    
    print("=== Testing Task Distribution with Shared MQTT Subscriptions ===")
    
    # Create multiple workers (subscribers)
    workers = []
    for i in range(3):
        worker = AetherMagic(config)
        
        # Each worker listens for tasks
        await worker.listen('test-job', 'process-data', 'batch1', 'perform', 'worker-group',
                          lambda job, task, context, tid, action, data: 
                          print(f"Worker {i} received task {tid}: {data}"))
        
        workers.append(worker)
    
    # Create publisher
    publisher = AetherMagic(config)
    
    # Start workers
    print("Starting workers...")
    worker_tasks = []
    for i, worker in enumerate(workers):
        task = asyncio.create_task(worker.work())
        worker_tasks.append(task)
        print(f"Worker {i} started")
    
    # Give workers time to connect and subscribe
    await asyncio.sleep(2)
    
    # Publish multiple tasks
    print("\nPublishing tasks...")
    for task_id in range(10):
        await publisher.perform(
            'test-job', 
            'process-data', 
            'batch1', 
            f'task-{task_id:03d}', 
            {'data': f'test-data-{task_id}', 'worker_id': task_id}
        )
        print(f"Published task-{task_id:03d}")
        await asyncio.sleep(0.1)  # Small delay between tasks
    
    # Let workers process tasks
    print("\nProcessing tasks for 10 seconds...")
    await asyncio.sleep(10)
    
    # Stop workers
    print("\nStopping workers...")
    for task in worker_tasks:
        task.cancel()
    
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_task_distribution())