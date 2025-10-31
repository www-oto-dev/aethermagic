# Task Distribution Example

This example demonstrates how AetherMagic distributes tasks among multiple workers using MQTT shared subscriptions.

## How it works

1. **Publisher** sends tasks to specific topics with unique task IDs
2. **Multiple workers** subscribe to a shared topic using wildcards  
3. **MQTT broker** automatically distributes each task to only ONE worker
4. **No duplicate processing** - each task is handled by exactly one worker

## Example Usage

### Starting Multiple Workers

```python
import asyncio
from aethermagic import AetherMagic

async def start_worker(worker_id):
    # Each worker connects to the same MQTT broker
    aether = AetherMagic('localhost', 1883, 'production-cluster')
    
    # All workers subscribe to the same job with shared subscription
    # This creates: $share/production-cluster_image-processing_workers/production-cluster/image-processing/resize/batch1/+/perform
    await aether.listen('image-processing', 'resize', 'batch1', 'perform', 'workers',
                       lambda job, task, context, tid, action, data: 
                       process_image(worker_id, tid, data))
    
    # Start processing
    await aether.work()

def process_image(worker_id, task_id, data):
    print(f"Worker {worker_id} processing task {task_id}: {data['image_url']}")
    # Process the image here...
    
# Start 3 workers
async def main():
    workers = []
    for i in range(3):
        task = asyncio.create_task(start_worker(i))
        workers.append(task)
    
    await asyncio.gather(*workers)

asyncio.run(main())
```

### Publishing Tasks

```python
import asyncio
from aethermagic import AetherMagic

async def publish_tasks():
    publisher = AetherMagic('localhost', 1883, 'production-cluster')
    
    # Publish multiple image processing tasks
    images = [
        'https://example.com/image1.jpg',
        'https://example.com/image2.jpg', 
        'https://example.com/image3.jpg',
        'https://example.com/image4.jpg',
        'https://example.com/image5.jpg'
    ]
    
    for i, image_url in enumerate(images):
        task_id = f'img-{i:03d}'
        
        # Each task goes to: production-cluster/image-processing/resize/batch1/img-001/perform
        # But workers subscribe to: $share/production-cluster_image-processing_workers/production-cluster/image-processing/resize/batch1/+/perform
        await publisher.perform('image-processing', 'resize', 'batch1', task_id, {
            'image_url': image_url,
            'target_size': '800x600'
        })
        
        print(f"Published task {task_id}")

asyncio.run(publish_tasks())
```

## Expected Output

**Publisher:**
```
Published task img-000
Published task img-001  
Published task img-002
Published task img-003
Published task img-004
```

**Workers (distributed automatically):**
```
Worker 0 processing task img-000: https://example.com/image1.jpg
Worker 1 processing task img-001: https://example.com/image2.jpg  
Worker 2 processing task img-002: https://example.com/image3.jpg
Worker 0 processing task img-003: https://example.com/image4.jpg
Worker 1 processing task img-004: https://example.com/image5.jpg
```

Notice how each task is processed by exactly one worker, and the load is automatically balanced!

## MQTT Topic Format

- **Publishing**: `{union}/{job}/{task}/{context}/{tid}/{action}`
- **Shared Subscription**: `$share/{union}_{job}_{workgroup}/{union}/{job}/{task}/{context}/+/{action}`

This ensures that:
- Tasks are published to specific topic paths
- Workers use shared subscriptions for automatic load balancing
- Only `perform` actions use shared subscriptions
- Status updates use regular subscriptions for monitoring