#!/usr/bin/env python3
"""
Simple test to check message processing after fix
"""

import asyncio
import json
from src.aethermagic.magic import AetherMagic
from src.aethermagic.protocols import ConnectionConfig, ProtocolType

async def simple_test():
    """Simple test with manual message injection"""
    
    print("=== Simple Multiple Task Test ===")
    print()
    
    # Use direct constructor to properly set union
    aether = AetherMagic(
        protocol_type=ProtocolType.MQTT,
        host='localhost',
        port=1883,
        union='test'
    )
    
    # Mock connected state
    aether._MultiProtocolAetherMagic__connected = True
    
    received_tasks = []
    
    def handle_task(action, tid, data, fulldata):
        print(f"🎯 TASK RECEIVED: {tid} -> {data}")
        received_tasks.append({'action': action, 'tid': tid, 'data': data})
    
    # Add listener
    await aether.subscribe(
        job='test-job',
        workgroup='test-group', 
        task='test-task',
        context='test-context',
        tid='+',
        action='perform',
        handler_func=handle_task
    )
    
    print(f"Listeners: {len(aether._MultiProtocolAetherMagic__listeners)}")
    
    # Manually add messages to incoming queue (simulate multiple receives)
    messages = [
        {
            'topic': 'test/test-job/test-task/test-context/task-001/perform',
            'payload': json.dumps({
                'action': 'perform',
                'status': 'initialized', 
                'progress': 0,
                'data': {'file': 'image1.jpg'},
                'host': 'publisher', 'client': 'pub1',
                'job': '', 'workgroup': '', 'task': '', 'context': '', 'tid': ''
            })
        },
        {
            'topic': 'test/test-job/test-task/test-context/task-002/perform',
            'payload': json.dumps({
                'action': 'perform',
                'status': 'initialized',
                'progress': 0, 
                'data': {'file': 'image2.jpg'},
                'host': 'publisher', 'client': 'pub1',
                'job': '', 'workgroup': '', 'task': '', 'context': '', 'tid': ''
            })
        }
    ]
    
    print("Processing first message...")
    aether._MultiProtocolAetherMagic__incoming.append(messages[0])
    await aether._MultiProtocolAetherMagic__process_incoming()
    
    print(f"Received after first: {len(received_tasks)}")
    
    print("Processing second message...")
    aether._MultiProtocolAetherMagic__incoming.append(messages[1])
    await aether._MultiProtocolAetherMagic__process_incoming()
    
    print(f"Received after second: {len(received_tasks)}")
    
    print(f"Total tasks received: {len(received_tasks)}")
    for task in received_tasks:
        print(f"  {task}")
    
    if len(received_tasks) == 2:
        print("✅ SUCCESS: Both tasks processed!")
    else:
        print("❌ PROBLEM: Not all tasks processed")

if __name__ == "__main__":
    asyncio.run(simple_test())