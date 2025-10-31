#!/usr/bin/env python3
"""
AetherMagic demonstration with different protocols
Run without arguments for interactive selection
"""

import asyncio
import sys
import time
from aethermagic import AetherMagic, ProtocolType, AetherTask


class ProtocolDemo:
    def __init__(self):
        self.protocols = {
            '1': ('Redis Pub/Sub', self.demo_redis),
            '2': ('HTTP/WebSocket', self.demo_http),  
            '3': ('ZeroMQ', self.demo_zeromq),
            '4': ('MQTT (Original)', self.demo_mqtt),
            '5': ('Redis Streams', self.demo_redis_streams),
        }
    
    def show_menu(self):
        print("\n" + "="*50)
        print("AetherMagic Multi-Protocol Demo")
        print("="*50)
        print("Choose protocol for demonstration:")
        print()
        
        for key, (name, _) in self.protocols.items():
            print(f"  {key}. {name}")
        
        print("  0. Exit")
        print()
        
        choice = input("Your choice: ").strip()
        return choice
    
    async def demo_redis(self):
        """Redis Pub/Sub demo"""
        print("\n🔴 Starting Redis Pub/Sub demo...")
        print("Make sure Redis is running on localhost:6379")
        
        try:
            aether = AetherMagic(
                protocol_type=ProtocolType.REDIS,
                host='localhost',
                port=6379,
                union='demo'
            )
            
            await self._run_worker_demo(aether, "Redis")
            
        except Exception as e:
            print(f"❌ Redis error: {e}")
            print("Make sure Redis is running: docker run -d -p 6379:6379 redis")
    
    async def demo_redis_streams(self):
        """Redis Streams demo"""
        print("\n🔴 Starting Redis Streams demo...")
        
        try:
            aether = AetherMagic(
                protocol_type=ProtocolType.REDIS,
                host='localhost',
                port=6379,
                union='demo',
                use_streams=True,
                consumer_group='demo_workers',
                consumer_name=f'worker_{int(time.time())}'
            )
            
            await self._run_worker_demo(aether, "Redis Streams")
            
        except Exception as e:
            print(f"❌ Redis Streams error: {e}")
    
    async def demo_http(self):
        """HTTP/WebSocket demo"""
        print("\n🌐 Starting HTTP/WebSocket demo...")
        
        try:
            # Start server in background
            server = AetherMagic(
                protocol_type=ProtocolType.HTTP,
                host='localhost',
                port=8888,
                union='demo',
                mode='server'
            )
            
            # Start server
            server_task = asyncio.create_task(server.main())
            await asyncio.sleep(0.5)  # Give server time to start
            
            print("✅ HTTP server started on port 8888")
            
            # Now client
            client = AetherMagic(
                protocol_type=ProtocolType.HTTP,
                host='localhost', 
                port=8888,
                union='demo',
                mode='client'
            )
            
            await self._run_worker_demo(client, "HTTP/WebSocket")
            
        except Exception as e:
            print(f"❌ HTTP/WebSocket error: {e}")
    
    async def demo_zeromq(self):
        """ZeroMQ demo"""
        print("\n⚡ Starting ZeroMQ demo...")
        
        try:
            aether = AetherMagic(
                protocol_type=ProtocolType.ZEROMQ,
                host='localhost',
                port=5555,
                union='demo',
                pattern='pubsub'
            )
            
            await self._run_worker_demo(aether, "ZeroMQ")
            
        except Exception as e:
            print(f"❌ ZeroMQ error: {e}")
            print("Make sure pyzmq is installed: pip install pyzmq")
    
    async def demo_mqtt(self):
        """MQTT demo (original)"""
        print("\n📡 Starting MQTT demo...")
        print("Make sure MQTT broker is running on localhost:1883")
        
        try:
            aether = AetherMagic(
                protocol_type=ProtocolType.MQTT,
                host='localhost',
                port=1883,
                union='demo'
            )
            
            await self._run_worker_demo(aether, "MQTT")
            
        except Exception as e:
            print(f"❌ MQTT error: {e}")
            print("Install broker: docker run -d -p 1883:1883 eclipse-mosquitto")
    
    async def _run_worker_demo(self, aether, protocol_name):
        """Common code for worker demonstration"""
        
        print(f"🚀 Creating worker for {protocol_name}...")
        
        # Task counter
        task_counter = 0
        
        async def handle_task(ae_task, data):
            nonlocal task_counter
            task_counter += 1
            
            print(f"  📋 Task #{task_counter}: {data}")
            print(f"  ⏳ Starting processing...")
            
            # Progress 25%
            await ae_task.status(25)
            print(f"  📊 Progress: 25%")
            await asyncio.sleep(0.5)
            
            # Progress 50%
            await ae_task.status(50)  
            print(f"  📊 Progress: 50%")
            await asyncio.sleep(0.5)
            
            # Progress 75%
            await ae_task.status(75)
            print(f"  📊 Progress: 75%")
            await asyncio.sleep(0.5)
            
            # Completion
            result = {
                "processed": data.get("input", "unknown"),
                "protocol": protocol_name,
                "task_id": task_counter,
                "timestamp": time.time()
            }
            
            await ae_task.complete(True, result)
            print(f"  ✅ Task #{task_counter} completed!")
            print(f"  📤 Result: {result}")
        
        # Create worker
        task = AetherTask(
            job='demo',
            task='process_data',
            context='test',
            on_perform=handle_task
        )
        
        print(f"  👷 Worker ready and waiting for tasks...")
        await task.idle()
        
        # Start client to send test tasks
        asyncio.create_task(self._send_test_tasks(aether, protocol_name))
        
        # Start main loop
        print(f"  🔄 Starting {protocol_name} loop...")
        await aether.main()
    
    async def _send_test_tasks(self, aether, protocol_name):
        """Send test tasks"""
        await asyncio.sleep(2)  # Give worker time to prepare
        
        print(f"\n📨 Sending test tasks via {protocol_name}...")
        
        # Client handlers
        async def on_status(ae_task, complete, succeed, progress, data):
            if complete:
                status = "✅ Success" if succeed else "❌ Error"
                print(f"  🏁 Task completed: {status}")
            else:
                print(f"  📈 Progress received: {progress}%")
        
        async def on_complete(ae_task, succeed, data):
            print(f"  🎯 Final result: {data}")
        
        # Send several test tasks
        for i in range(3):
            print(f"\n  📤 Sending task #{i+1}...")
            
            client_task = AetherTask(
                job='demo',
                task='process_data', 
                context='test',
                on_status=on_status,
                on_complete=on_complete
            )
            
            test_data = {
                "input": f"test_data_{i+1}",
                "batch_size": 100 + i * 50,
                "priority": "normal",
                "sender": f"{protocol_name}_client"
            }
            
            await client_task.perform(test_data)
            await asyncio.sleep(3)  # Interval between tasks
        
        print(f"\n📬 All test tasks sent via {protocol_name}")
        
        # Give time for processing
        await asyncio.sleep(10)
        print(f"\n🏃 Demo {protocol_name} completed")
    
    async def run(self):
        """Main demo loop"""
        print("Welcome to AetherMagic demonstration!")
        
        while True:
            choice = self.show_menu()
            
            if choice == '0':
                print("\n👋 Goodbye!")
                break
            
            if choice in self.protocols:
                name, demo_func = self.protocols[choice]
                print(f"\n🎬 Starting demo: {name}")
                
                try:
                    await demo_func()
                except KeyboardInterrupt:
                    print(f"\n⏸️  Demo {name} interrupted by user")
                except Exception as e:
                    print(f"\n💥 Unexpected error in {name}: {e}")
                
                input("\n⏎ Press Enter to return to menu...")
            else:
                print("❌ Invalid choice. Please try again.")


if __name__ == "__main__":
    demo = ProtocolDemo()
    
    try:
        asyncio.run(demo.run())
    except KeyboardInterrupt:
        print("\n\n👋 Program terminated by user")
    except Exception as e:
        print(f"\n💥 Critical error: {e}")