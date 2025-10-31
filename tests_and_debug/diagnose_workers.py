#!/usr/bin/env python3
"""
Diagnose why both workers receive the same task but don't process it
"""

import asyncio
import json
from src.aethermagic.magic import AetherMagic
from src.aethermagic.protocols import ConnectionConfig, ProtocolType

class DiagnosticProtocol:
    """Protocol to diagnose shared subscription issues"""
    
    def __init__(self, config, worker_id):
        self.config = config
        self.worker_id = worker_id
        self.connected = False
        self.subscribed_topics = []
        self.received_messages = []
        self.published_messages = []
        
    async def connect(self):
        self.connected = True
        print(f"Worker-{self.worker_id}: Connected")
        return True
        
    async def disconnect(self):
        self.connected = False
        return True
        
    async def publish(self, topic, message, retain=False):
        self.published_messages.append({
            'topic': topic,
            'action': message.action,
            'status': message.status,
            'data': message.data
        })
        print(f"Worker-{self.worker_id}: 📤 Published {message.action} ({message.status}) to {topic}")
        return True
        
    async def subscribe(self, topic, callback=None):
        print(f"Worker-{self.worker_id}: 📥 Subscribed to {topic}")
        self.subscribed_topics.append(topic)
        return True
        
    async def unsubscribe(self, topic):
        print(f"Worker-{self.worker_id}: ❌ Unsubscribed from {topic}")
        if topic in self.subscribed_topics:
            self.subscribed_topics.remove(topic)
        return True
        
    async def receive_messages(self):
        """Simulate receiving the same task (like your issue)"""
        messages = []
        
        # Simulate both workers getting the same task (broken shared subscription)
        if (self.subscribed_topics and 
            any('$share/' in topic and 'perform' in topic for topic in self.subscribed_topics)):
            
            # Both workers get the same task
            task_message = {
                'topic': f'{self.config.union}/engine/generate-website-content/x/problem-task-123/perform',
                'payload': json.dumps({
                    'action': 'perform',
                    'status': 'initialized',
                    'progress': 0,
                    'data': {'url': 'https://example.com/content', 'type': 'article'},
                    'host': 'publisher', 'client': 'pub1',
                    'job': '', 'workgroup': '', 'task': '', 'context': '', 'tid': ''
                })
            }
            
            messages.append(task_message)
            self.received_messages.append(task_message)
            
            print(f"Worker-{self.worker_id}: 📨 Received task problem-task-123 (total: {len(self.received_messages)})")
        
        return messages
        
    def generate_topic(self, job, task, context, tid, action, shared=False, workgroup=""):
        base_topic = f'{self.config.union}/{job}/{task}/{context}/{tid}/{action}'
        
        if shared and action == 'perform' and workgroup:
            shared_group = f'{self.config.union}_{job}_{workgroup}'
            topic = f'$share/{shared_group}/{base_topic}'
        else:
            topic = base_topic
            
        return topic
        
    def parse_topic(self, topic):
        parts = topic.split('/')
        if len(parts) >= 6:
            return {
                'union': parts[0],
                'job': parts[1], 
                'task': parts[2],
                'context': parts[3],
                'tid': parts[4],
                'action': parts[5]
            }
        return {}

async def diagnose_shared_subscription_issue():
    """Diagnose why both workers get same task"""
    
    print("=== Diagnosing Shared Subscription Issue ===")
    print()
    
    workers = []
    
    # Create 2 workers (like your setup)
    for worker_id in [1, 2]:
        aether = AetherMagic(
            protocol_type=ProtocolType.MQTT,
            host='localhost',
            port=1883,
            union='production'
        )
        
        # Replace with diagnostic protocol
        diagnostic_protocol = DiagnosticProtocol(aether.config, worker_id)
        aether.protocol = diagnostic_protocol
        
        # Track what each worker does
        worker_state = {
            'id': worker_id,
            'aether': aether,
            'protocol': diagnostic_protocol,
            'tasks_handled': 0,
            'task_ids_seen': set()
        }
        
        def make_handler(worker_state):
            def handle_task(action, tid, data, fulldata):
                worker_state['tasks_handled'] += 1
                worker_state['task_ids_seen'].add(tid)
                
                print(f"🎯 Worker-{worker_state['id']} HANDLER: Processing task {tid}")
                print(f"   Data: {data}")
                print(f"   Total tasks handled by this worker: {worker_state['tasks_handled']}")
                
                # Simulate some processing
                print(f"   Worker-{worker_state['id']} doing work on {tid}...")
                
            return handle_task
        
        # Subscribe to tasks
        await aether.subscribe(
            job='engine',
            workgroup='workers',  # Same workgroup = shared subscription
            task='generate-website-content', 
            context='x',
            tid='+',
            action='perform',
            handler_func=make_handler(worker_state)
        )
        
        workers.append(worker_state)
    
    print(f"Created {len(workers)} workers with shared subscription")
    print()
    
    # Start both workers
    worker_tasks = []
    for worker in workers:
        print(f"Starting Worker-{worker['id']}...")
        task = asyncio.create_task(worker['aether'].main())
        worker_tasks.append(task)
    
    # Let them run and observe the issue
    print("\nRunning workers for 10 cycles...")
    
    for cycle in range(10):
        await asyncio.sleep(0.8)
        
        print(f"\n--- Cycle {cycle + 1} Status ---")
        for worker in workers:
            protocol = worker['protocol']
            print(f"Worker-{worker['id']}:")
            print(f"  Tasks handled: {worker['tasks_handled']}")
            print(f"  Task IDs seen: {worker['task_ids_seen']}")
            print(f"  Messages received: {len(protocol.received_messages)}")
            print(f"  Messages published: {len(protocol.published_messages)}")
            print(f"  Subscriptions: {len(protocol.subscribed_topics)}")
            
            # Show recent publications
            if protocol.published_messages:
                recent = protocol.published_messages[-3:]  # Last 3
                recent_actions = [f"{p['action']}({p['status']})" for p in recent]
                print(f"  Recent publications: {recent_actions}")
    
    # Stop workers
    print("\nStopping workers...")
    for worker in workers:
        await worker['aether'].stop()
    
    for task in worker_tasks:
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except:
            task.cancel()
    
    # Analysis
    print("\n=== ANALYSIS ===")
    
    total_tasks_handled = sum(w['tasks_handled'] for w in workers)
    unique_tasks = set()
    for w in workers:
        unique_tasks.update(w['task_ids_seen'])
    
    print(f"Total task processing calls: {total_tasks_handled}")
    print(f"Unique task IDs processed: {len(unique_tasks)} -> {unique_tasks}")
    
    # Check if both workers got the same task
    if len(workers) >= 2:
        worker1_tasks = workers[0]['task_ids_seen']
        worker2_tasks = workers[1]['task_ids_seen']
        overlap = worker1_tasks & worker2_tasks
        
        if overlap:
            print(f"❌ PROBLEM: Both workers processed same tasks: {overlap}")
            print("   This indicates shared subscription is NOT working")
            print("   Both workers are getting the same messages instead of load balancing")
        else:
            print("✅ GOOD: Workers processed different tasks (proper load balancing)")
    
    # Check for infinite receiving
    total_received = sum(len(w['protocol'].received_messages) for w in workers)
    if total_received > 20:
        print(f"⚠️  WARNING: Too many message receptions ({total_received})")
        print("   This suggests messages are not being acknowledged/removed")
    
    # Check if tasks were actually processed vs just received
    if total_received > 0 and total_tasks_handled == 0:
        print("❌ CRITICAL: Messages received but NO tasks processed")
        print("   Check if handlers are being called or if deduplication is blocking")
    elif total_received > total_tasks_handled * 2:
        print("⚠️  Issue: Much more receiving than processing")
        print("   Suggests deduplication or other filtering")

if __name__ == "__main__":
    asyncio.run(diagnose_shared_subscription_issue())