from datetime import datetime, timedelta, timezone
import asyncio
import json
import re

import certifi
import aiomqtt


MQTT_BROKER = 'mqtt.oto.dev'
MQTT_PORT = 8883
MQTT_USER = ''
MQTT_PASSWORD = ''


# Configuration
MQTT_CONFIG = {
    "server": MQTT_BROKER,
    "port": MQTT_PORT,
    "user": MQTT_USER,
    "password": MQTT_PASSWORD,
    "ssl": True,
    "identifier": "repeater-client"
}

TIMEOUT_MIN = 3  # seconds
TIMEOUT_STEP = 3 # seconds (0-N), each timeout is: new_timeout = timeout + step
TIMEOUT_MAX = 300  # seconds


class MQTTRepeater:
    def __init__(self):
        self._tasks = {}  # tid -> { payload, timeout, timestamp, topic }

    async def _new_mqtt(self):
        tls_params = aiomqtt.TLSParameters(ca_certs=certifi.where())
        return aiomqtt.Client(
            hostname=MQTT_CONFIG["server"],
            port=MQTT_CONFIG["port"],
            username=MQTT_CONFIG["user"],
            password=MQTT_CONFIG["password"],
            identifier=MQTT_CONFIG["identifier"],
            tls_params=tls_params if MQTT_CONFIG["ssl"] else None,
            timeout=10,
            keepalive=10,
            clean_session=True,
        )

    async def _handle_message(self, message):
        topic = str(message.topic)
        payload = message.payload.decode("utf-8")
        parts = topic.split("/")

        if len(parts) != 6:
            return  # not our format

        union, job, task, context, tid, action = parts

        if action not in ("perform", "status", "complete"):
            return

        now = datetime.now(timezone.utc)

        # Clear list of tasks in queue by union: union/repeater/clear/*/*/perform
        if action == "perform" and job == "repeater" and task == "clear":
            removed = []
            for existing_tid, info in list(self._tasks.items()):
                if info.get("union") == union:
                    removed.append(existing_tid)
                    del self._tasks[existing_tid]
            print(f"🧹 Cleared {len(removed)} tasks for union: {union}")
            return

        if action == "perform":
            previous = self._tasks.get(tid, {})
            preserved_timeout = max(previous.get("timeout", TIMEOUT_MIN), TIMEOUT_MIN)  

            
            if previous.get("topic", "") == "":
                self._tasks[tid] = {
                    "tracking" : True,
                    "payload": payload,
                    "timeout": preserved_timeout,
                    #"timestamp": now,
                    "timestamp": previous.get("timestamp", now), # Not overwritinh the timestemp
                    "topic": topic,
                    "qos": message.qos,
                    "retain": message.retain,
                    "union": union,
                }
            
                print(f"🆕 Added task for tracking: tid={tid}, union={union}, action={action}, topic={topic}")
            
            #else:
            #    print(f"〰️ Skipping retracking task: tid={tid}, union={union}, action={action}, topic={topic}")


        elif action in ("status", "complete"):
            if tid in self._tasks:
                removed = self._tasks.pop(tid)
                print(f"✅ Removed task: tid={tid}, union={union}, action={action}, topic(removed)={removed['topic']}")
            else:
                print(f"⚠️ Got {action} for unknown tid={tid}")


    async def _resend_loop(self, client):
        while True:
            now = datetime.now(timezone.utc)
            to_remove = []

            for tid, info in list(self._tasks.items()):

                if info["timeout"] > TIMEOUT_MAX:
                    print(f"✖️ Removing untracked timeouted task with tid={tid}, removing from queue.")
                    to_remove.append(tid)                    
                    continue

                delta = (now - info["timestamp"]).total_seconds()
                if delta >= info["timeout"]:

                    new_timeout = info['timeout'] + TIMEOUT_STEP


                    print(f"🔁 Resending task: tid={tid}, topic={info['topic']}, "
                          f"after timeout={info['timeout']}, new timeout={new_timeout}s")

                    # Update timestamp and double timeout
                    #self._tasks[tid]["timestamp"] = now # NOT overwrinting the timestamp
                    self._tasks[tid]["timeout"] = new_timeout

                    if new_timeout > TIMEOUT_MAX:
                        print(f"🕑 Timeout exceeded for tid={tid}, removing from tracking.")
                        self._tasks[tid]["tracking"] = False
                        
                    # !IMPORTANT: RESENDING AFTER UPDATING THE TASK
                    # Resend the message with original qos and retain
                    await client.publish(
                        info["topic"],
                        payload=info["payload"],
                        qos=info.get("qos", 0),
                        retain=info.get("retain", False)
                    )



            for tid in to_remove:
                del self._tasks[tid]

            await asyncio.sleep(5)


    async def run(self):
        client = await self._new_mqtt()

        async with client:
            await client.subscribe("#")  # подписываемся на все топики
            asyncio.create_task(self._resend_loop(client))

            async for message in client.messages:
                await self._handle_message(message)



# Entry point
async def main():
    repeater = MQTTRepeater()
    await repeater.run()


# Only run if script is executed directly
if __name__ == "__main__":
    asyncio.run(main())