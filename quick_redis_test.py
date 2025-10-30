#!/usr/bin/env python3
"""
Quick Redis protocol test
Requires running Redis on localhost:6379
"""

import asyncio
import time
from aethermagic import AetherMagic, ProtocolType, AetherTask


async def redis_quick_test():
    """Quick Redis Pub/Sub test"""
    print("🔴 Testing Redis protocol...")
    
    try:
        # Create Redis instance
        aether = AetherMagic(
            protocol_type=ProtocolType.REDIS,
            host='localhost',
            port=6379,
            union='quick_test'
        )
        
        print("✅ AetherMagic with Redis created")
        
        # Task counter
        completed_tasks = []
        
        async def handle_task(ae_task, data):
            print(f"  📋 Processing: {data}")
            
            # Quick processing
            await ae_task.status(50)
            await asyncio.sleep(0.2)
            
            await ae_task.status(100)
            result = {
                "input": data,
                "processed_at": time.time(),
                "protocol": "redis"
            }
            
            await ae_task.complete(True, result)
            completed_tasks.append(result)
            print(f"  ✅ Task completed: {result}")
        
        # Create worker
        worker_task = AetherTask(
            job='test',
            task='quick_work',
            context='demo',
            on_perform=handle_task
        )
        
        print("  👷 Registering worker...")
        await worker_task.idle()
        
        # Send tasks in background
        async def send_tasks():
            await asyncio.sleep(1)  # Give worker time to prepare
            
            for i in range(2):
                print(f"  📤 Sending task {i+1}...")
                
                client_task = AetherTask(
                    job='test',
                    task='quick_work',
                    context='demo'
                )
                
                await client_task.perform({
                    "test_id": i+1,
                    "data": f"sample_data_{i+1}"
                })
                
                await asyncio.sleep(0.5)
        
        # Start sending tasks
        asyncio.create_task(send_tasks())
        
        print("  🔄 Starting processing loop...")
        
        # Run for a short time
        start_time = time.time()
        main_task = asyncio.create_task(aether.main())
        
        # Wait a few seconds or until tasks complete
        while time.time() - start_time < 5:
            await asyncio.sleep(0.1)
            
            # If all tasks completed, stop
            if len(completed_tasks) >= 2:
                break
        
        main_task.cancel()
        
        print(f"🎯 Tasks processed: {len(completed_tasks)}")
        for task in completed_tasks:
            print(f"  - {task}")
        
        if len(completed_tasks) >= 1:
            print("🎉 Redis protocol working!")
            return True
        else:
            print("⚠️  Redis protocol didn't process tasks")
            return False
            
    except Exception as e:
        print(f"❌ Redis test error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 50)
    print("🚀 Quick Redis Protocol Test")  
    print("=" * 50)
    print()
    print("Make sure Redis is running:")
    print("  docker run -d -p 6379:6379 redis")
    print("  or")
    print("  redis-server")
    print()
    
    success = await redis_quick_test()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Test passed successfully!")
        print("🚀 AetherMagic ready to work with Redis!")
    else:
        print("❌ Test failed")
        print("💡 Check that Redis is running and accessible")
    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted")
    except Exception as e:
        print(f"\n💥 Error: {e}")