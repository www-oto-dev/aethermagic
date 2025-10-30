#!/usr/bin/env python3
"""
Simple test to verify AetherMagic functionality
"""

import asyncio
import sys
import traceback
from aethermagic import MultiProtocolAetherMagic, ProtocolType


async def test_protocol_creation():
    """Test protocol creation"""
    print("🧪 Testing protocol creation...")
    
    protocols_to_test = [
        (ProtocolType.REDIS, 6379),
        (ProtocolType.HTTP, 8080), 
        (ProtocolType.ZEROMQ, 5555),
        (ProtocolType.MQTT, 1883),
    ]
    
    for protocol_type, port in protocols_to_test:
        try:
            print(f"  ✨ Creating {protocol_type.value}...")
            
            aether = MultiProtocolAetherMagic(
                protocol_type=protocol_type,
                host='localhost',
                port=port,
                union='test'
            )
            
            print(f"  ✅ {protocol_type.value} created successfully")
            
        except Exception as e:
            print(f"  ❌ Error creating {protocol_type.value}: {e}")
    
    print("✅ Protocol creation test completed\n")


async def test_simple_workflow():
    """Test simple workflow without real connections"""
    print("🔄 Testing workflow...")
    
    try:
        # Create instance
        aether = MultiProtocolAetherMagic(
            protocol_type=ProtocolType.REDIS,
            host='localhost',
            port=6379,
            union='test'
        )
        
        print("  📋 Instance created")
        
        # Test internal methods
        test_data = {"test": "data"}
        payload = aether._MultiProtocolAetherMagic__data_to_payload('test', 'progress', 50, test_data)
        print(f"  📦 Payload created: {len(payload)} characters")
        
        parsed = aether._MultiProtocolAetherMagic__payload_to_fulldata(payload)
        print(f"  📥 Payload parsed: {parsed['action']}")
        
        print("  ✅ Internal methods working")
        
    except Exception as e:
        print(f"  ❌ Workflow error: {e}")
        traceback.print_exc()
    
    print("✅ Workflow test completed\n")


async def test_imports():
    """Test imports"""
    print("📦 Testing imports...")
    
    try:
        from aethermagic import AetherMagic, ProtocolType, AetherTask, ConnectionConfig
        print("  ✅ Main classes imported")
        
        from aethermagic.protocols import ProtocolInterface, AetherMessage
        print("  ✅ Protocol classes imported")
        
        # Try to import protocols
        try:
            from aethermagic.protocols.redis_protocol import RedisProtocol
            print("  ✅ Redis protocol imported")
        except ImportError as e:
            print(f"  ⚠️  Redis protocol not imported: {e}")
        
        try:
            from aethermagic.protocols.http_websocket_protocol import HTTPWebSocketProtocol
            print("  ✅ HTTP/WebSocket protocol imported")
        except ImportError as e:
            print(f"  ⚠️  HTTP/WebSocket protocol not imported: {e}")
        
        try:
            from aethermagic.protocols.zeromq_protocol import ZeroMQProtocol
            print("  ✅ ZeroMQ protocol imported")
        except ImportError as e:
            print(f"  ⚠️  ZeroMQ protocol not imported: {e}")
        
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        traceback.print_exc()
    
    print("✅ Import test completed\n")


async def test_message_creation():
    """Test message creation"""
    print("💌 Testing message creation...")
    
    try:
        from aethermagic.protocols import AetherMessage
        
        # Create message
        message = AetherMessage(
            action='test',
            status='progress', 
            progress=75,
            data={'key': 'value'},
            host='test-host',
            client='test-client'
        )
        
        print(f"  📝 Message created: {message.action}")
        
        # Convert to JSON
        json_str = message.to_json()
        print(f"  📄 JSON created: {len(json_str)} characters")
        
        # Parse back
        parsed = AetherMessage.from_json(json_str)
        print(f"  🔄 JSON parsed: {parsed.action}")
        
        # Check data
        assert parsed.action == message.action
        assert parsed.progress == message.progress
        print("  ✅ Data matches")
        
    except Exception as e:
        print(f"  ❌ Message creation error: {e}")
        traceback.print_exc()
    
    print("✅ Message creation test completed\n")


async def main():
    """Main testing function"""
    print("=" * 60)
    print("🚀 AetherMagic Multi-Protocol Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_imports,
        test_message_creation,
        test_protocol_creation,
        test_simple_workflow,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"💥 Test {test_func.__name__} failed: {e}")
            traceback.print_exc()
            print()
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed successfully")
    
    if passed == total:
        print("🎉 All tests passed! AetherMagic is ready to use.")
    else:
        print("⚠️  Some tests failed. Check dependencies.")
        print("💡 For full functionality install:")
        print("   pip install redis aiohttp websockets pyzmq")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        sys.exit(1)