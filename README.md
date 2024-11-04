# AetherMagic 
# Communications between microservices over MQTT

The goal is to create communication between microservices, using such advantages as:

- Scaling (multiple microservices to perform one group of tasks)
- Distribution of tasks (only one microserver receives a task in a group)
- Distribution of access rights for specific tasks/roles (setting or execution) and division, if necessary, by projects (by configuring access rights on the server side in the MQTT broker)


## Installation

`pip install aethermagic`


## Example

### To launch a task on master-server / separate process:

```
from aethermagic import AetherMagic, aether

async def complete(ae, success, output_data):
  # success => True / False
  # output_data => user-defined data unserialize from JSON
  print('complete')

async def status(ae, complete, success, progress, output_data):
  # complete => True / False
  # success => True / False
  # progress => 0...100
  # output_data => user-defined data unserialize from JSON
  print('status')

input_data = {} # user-defined data to serialize into JSON
await aether(None, 'worker', 'collect', on_complete=complete, on_status=status).perform(input_data)

```

### To perform task on worker-server / separate process:


```
from aethermagic import AetherMagic, aether


async def perform(ae, input_data):
  print('perform')
  # output_data => user-defined data unserialize from JSON

  success = sync_to_async(do_something_sync)(input_data)
  await ae.status(50)

  output_data = await do_something_async(input_data)

  await ae.status(50) # Optional
  await ae.complete(success, output_data)
  

await aether(None, 'worker', 'collect', on_perform=perform).idle()

```


### AetherMagic requires running or joining an existing async loop:

For example, in simple python app you can do it with the following code:

```
import threading
import asyncio
from aethermagic import AetherMagic

def startloop_telegram(self, args=[None]) -> None:

  async def starttask() -> None:

    aem = AetherMagic(server=settings.MQTT_BROKER, port=settings.MQTT_PORT, ssl=True, user=settings.MQTT_USER, password=settings.MQTT_PASSWORD, union=settings.AETHER_UNION)
    telegram = Telegram()

    async with asyncio.TaskGroup() as group:
      group.create_task(aem.main())
      #group.create_task(your_loop.main()) # Optional: You can create your own async loop

  asyncio.run(starttask())

thread = threading.Thread(target=startloop_telegram, args=[None])
thread.start()
thread.join() # Will wait for thread execution to complete ==> never
```
