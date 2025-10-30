#!/usr/bin/env python3
"""
Demo showing MQTT shared subscriptions for task distribution
"""

import asyncio
from src.aethermagic.protocols.mqtt_protocol import MQTTProtocol
from src.aethermagic.protocols import ConnectionConfig, ProtocolType, AetherMessage

def demo_topic_generation():
    """Demonstrate the topic generation matching your original format"""
    
    print("=== MQTT Topic Generation Demo ===")
    print()
    
    # Configuration matching your logs
    config = ConnectionConfig(ProtocolType.MQTT, 'lisboa-2025.release', 1883, union='lisboa-2025.release')
    protocol = MQTTProtocol(config)
    
    print("Configuration:")
    print(f"  Union: {config.union}")
    print(f"  Host: {config.host}:{config.port}")
    print()
    
    # Publishing topics (specific task IDs)
    print("Publishing topics (specific task IDs):")
    
    tasks = ['a2de67ca', 'b3ef78db', 'c4f089ec']
    for task_id in tasks:
        pub_topic = protocol.generate_topic(
            'illusion', 'redownload-images', 'x', task_id, 'perform', 
            shared=False
        )
        print(f"  Task {task_id}: {pub_topic}")
    
    print()
    
    # Subscription topics (with load balancing)
    print("Subscription topics (with shared load balancing):")
    
    workgroups = ['workgroup', 'team-a', 'team-b']
    for wg in workgroups:
        sub_topic = protocol.generate_topic(
            'illusion', 'redownload-images', 'x', '+', 'perform',
            shared=True, workgroup=wg
        )
        print(f"  Workgroup {wg}: {sub_topic}")
    
    print()
    
    # Non-shared subscriptions (for status updates)
    print("Non-shared subscriptions (status updates):")
    
    for action in ['status', 'progress', 'complete', 'error']:
        topic = protocol.generate_topic(
            'illusion', 'redownload-images', 'x', '+', action,
            shared=False
        )
        print(f"  Action {action}: {topic}")
    
    print()
    print("=== How Shared Subscriptions Work ===")
    print()
    print("1. Publisher sends tasks to specific topics:")
    print("   lisboa-2025.release/illusion/redownload-images/x/a2de67ca/perform")
    print("   lisboa-2025.release/illusion/redownload-images/x/b3ef78db/perform")
    print("   lisboa-2025.release/illusion/redownload-images/x/c4f089ec/perform")
    print()
    print("2. Multiple workers subscribe to shared topic:")
    print("   $share/lisboa-2025.release_illusion_workgroup/lisboa-2025.release/illusion/redownload-images/x/+/perform")
    print()
    print("3. MQTT broker distributes each task to only ONE worker in the shared group")
    print("   - Worker A gets task a2de67ca")
    print("   - Worker B gets task b3ef78db") 
    print("   - Worker C gets task c4f089ec")
    print()
    print("4. This ensures load balancing and prevents duplicate processing!")

if __name__ == "__main__":
    demo_topic_generation()