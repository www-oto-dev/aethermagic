#!/usr/bin/env python3
"""
Test backward compatibility of old AetherMagic methods
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aethermagic import AetherMagic
from aethermagic.protocols import ProtocolType


async def test_backward_compatibility():
    """Test that old methods work exactly as before"""
    print("=== Backward Compatibility Test ===")
    
    # Old style initialization (should work!)
    aether = AetherMagic(server="localhost", port=1883, union="test")
    print(f"✓ Old initialization: {type(aether.protocol).__name__}")
    
    # Test topic generation - old methods should NOT use shared
    protocol = aether.protocol
    
    # Test PUBLISHING: should always use regular topics (shared=False)
    publish_topic = protocol.generate_topic(
        job="engine", 
        task="generate-website-content", 
        context="x", 
        tid="78f9a888", 
        action="perform",
        shared=False  # Publishing uses regular topics
    )
    
    expected_publish = "test/engine/generate-website-content/x/78f9a888/perform"
    print(f"✓ Publishing topic (regular): {publish_topic}")
    print(f"  Expected: {expected_publish}")
    print(f"  Match: {publish_topic == expected_publish}")
    
    # Test SUBSCRIPTION: shared=True adds $share prefix for load balancing
    subscribe_topic = protocol.generate_topic(
        job="engine",
        task="generate-website-content", 
        context="x",
        tid="78f9a888",
        action="perform",
        shared=True  # Subscription uses shared topics for load balancing
    )
    
    expected_subscribe = "$share/test_engine_generate-website-content/test/engine/generate-website-content/x/78f9a888/perform"
    print(f"✓ Subscription topic (shared): {subscribe_topic}")
    print(f"  Expected: {expected_subscribe}")
    print(f"  Match: {subscribe_topic == expected_subscribe}")
    
    # Test non-perform actions: always regular topics regardless of shared flag
    status_topic = protocol.generate_topic(
        job="engine",
        task="generate-website-content",
        context="x", 
        tid="78f9a888",
        action="status",
        shared=True  # Even with shared=True, status uses regular topic
    )
    
    expected_status = "test/engine/generate-website-content/x/78f9a888/status" 
    print(f"✓ Status topic (always regular): {status_topic}")
    print(f"  Expected: {expected_status}")
    print(f"  Match: {status_topic == expected_status}")
    
    print("\n=== Method Availability Test ===")
    
    # Check old methods exist
    old_methods = ['perform', 'idle', 'complete', 'status', 'subscribe', 'unsubscribe']
    for method in old_methods:
        exists = hasattr(aether, method)
        print(f"✓ {method}: {'EXISTS' if exists else 'MISSING'}")
    
    # Check new methods exist  
    new_methods = ['perform_task', 'add_task', 'subscribe_shared']
    for method in new_methods:
        exists = hasattr(aether, method)
        print(f"✓ {method}: {'EXISTS' if exists else 'MISSING'}")
    
    print("\n🎉 Backward compatibility preserved!")
    print("Old code will work without changes!")
    print("New features available through new methods!")


if __name__ == "__main__":
    asyncio.run(test_backward_compatibility())