
import threading
from asyncio import Queue
import asyncio
from asgiref.sync import async_to_sync, sync_to_async
from functools import wraps

from uuid import uuid1

import json

from django.conf import settings

import certifi
import paho.mqtt.client as mqtt
import aiomqtt

import socket



class SUBSTATE:
     TO_SUBSCRIBE, SUBSCRIBED, TO_UNSUBSCRIBE, UNSUBSCRIBED  = range(4)



shared_instances = {}
shared_instances_lock = threading.Lock()


class AetherMagic:

	def __init__(self, server, port, ssl=True, user='', password='', union='default'):
		
		self.__listeners = []
		self.__outgoing = []
		self.__incoming = []
		self.__subscribed = []

		self.__server = server
		self.__port = port
		self.__ssl = ssl
		self.__user = user
		self.__password = password
		self.__union = union
		self.__mqtt = None

		self.__hostname = socket.gethostname()
		self.__identifier = str(uuid1())

		self.__share_tasks = True # Execute with load balancing, not with all workers at same time
		self.__action_in_topic = True # Required for shared tasks

		# sharing instance with thread
		self.__share_instance(self)



	def __share_instance(self, instance):

		global shared_instances
		global shared_instances_lock

		with shared_instances_lock:
			threadid = threading.get_ident()

			if instance is not None:
				shared_instances[threadid] = instance

		return


	def shared():

		instance = None

		global shared_instances
		global shared_instances_lock

		with shared_instances_lock:
			threadid = threading.get_ident()

			if threadid in shared_instances:
				instance = shared_instances[threadid]

		return instance


	async def __new_mqtt(self):

		tls_params = aiomqtt.TLSParameters(
		    ca_certs=certifi.where(),
		)		

		return aiomqtt.Client(
			hostname=self.__server,
			port=self.__port,
			username=self.__user if not self.__user == '' else None,
			password=self.__password if not self.__user == '' else None,
			identifier=self.__identifier,
			tls_context=None,
			tls_params=tls_params if self.__ssl else None,
			timeout=10,
			keepalive=10,
			clean_session=True,
			#max_queued_incoming_messages=1, # NOT USE: Cases WARNING - Message queue is full. Discarding message.
		)


	async def main(self):
		
		# New MQTT object for connection
		self.__mqtt = await self.__new_mqtt()

		failed_connection_interval = 10  # Seconds
		
		while True: # Loop to re-connect


			just_connected = True

			try:


				# Connection to MQTT. Leaving this block will disconnect
				async with self.__mqtt:
				# CONNECTED HERE

					print("MQTT: Connected")

					# While we do not have incomming actions to process
					#while len(self.__incoming) == 0:
					while True:

						# Sending online (within queue) if just connected
						if just_connected:
							await self.online("system", "", "online", self.__hostname, self.__identifier, {}, None)
							just_connected = False


						# Every reconnect it looses subscriptions inside mqtt, so: resubscribe
						await self.__subscribe_list(self.__mqtt)
						#self.__subscribed = []
						#for i in range(len(self.__listeners)): 
						#	if not (self.__listeners[i]['state'] == SUBSTATE.TO_UNSUBSCRIBE or self.__listeners[i]['state'] == SUBSTATE.UNSUBSCRIBED):
						#		self.__listeners[i]['state'] = SUBSTATE.TO_SUBSCRIBE
						
						# Subscribe and create list
						await self.__subscribe_required_listeners(self.__mqtt)

						# Sending outgoing
						#await self.__send_outgoing(self.__mqtt) #TODO: Do we need it here as well?

						# Recieving incoming
						has_incoming, has_perform = await self.__recieve_incoming(self.__mqtt)

						# Replying immediatly for some incomming messages
						await self.__reply_incoming_immediate()

						# Sending outgoing (if any new)
						await self.__send_outgoing(self.__mqtt)

						# Unsubscribe and update list
						await self.__unsubscribe_required_listeners(self.__mqtt)						
						
						# Processing incomming
						if has_incoming:
							
							# If there is a perform action - it is shared, we need to unsubscribe
							# to allow others to get tasks while we are executing this one
							# without counting us in order of recieving new task
							# For example, after recieving 'engine/build' we would like
							# to skip our turn for 'spider/collect' as well, as soon as we are busy
							if has_perform: await self.__unsubscribe_list__only_shared(self.__mqtt)
							
							# Processing incoming messages
							await self.__process_incoming()

						# Sleep to make possible another actions
						await asyncio.sleep(1)


				# DISCONNECTED HERE

				# Processing incoming messages
				#await self.__process_incoming()



			except aiomqtt.MqttError:
				print("MQTT: Connection lost; Reconnecting ...")
				await asyncio.sleep(failed_connection_interval)







	def __data_to_fulldata_(self, action, status, progress, data):
		return {
				"host" : self.__hostname,
				"client" : self.__identifier,

				"action" : action,
				"status" : status,
				"progress" : progress,

				"data" : data,

			}


	def __data_to_payload_(self, action, status, progress, data):

		fulldata = self.__data_to_fulldata_(action, status, progress, data)

		payload = json.dumps(fulldata)
		return payload


	def __payload_to_fulldata_(self, payload):

		try:
			fulldata = json.loads(payload)
		except Exception as err:   #json.decoder.JSONDecodeError
			print(f"Unexpected JSON pasrsing error {err=}, {type(err)=}")
			fulldata = self.__data_to_fulldata_('complete', 'failed', 0, {})

		return fulldata





	def __topic_for_listener_(self, listener):


		# Shared subscription for action == perform
		shared = '$share/' + self.__union + '_' + listener['job'] + '_' + listener['workgroup']
		if listener['action'] == 'perform' and self.__share_tasks: topic =  shared + '/'
		else: topic = ''

		# Main topic part
		topic = topic + self.__union + '/' + listener['job'] + '/' + listener['task'] + '/' + listener['context']
		
		# Including action
		if self.__action_in_topic: topic = topic + '/+/' + listener['action'] 
		else: topic = topic + '/#'


		return topic
		

	async def __subscribe_list(self, mqtt):

		for subscribed in self.__subscribed:
			await mqtt.subscribe(subscribed)


	async def __unsubscribe_list(self, mqtt):

		for subscribed in self.__subscribed:
			await mqtt.unsubscribe(subscribed)

	async def __unsubscribe_list__only_shared(self, mqtt):
		for subscribed in self.__subscribed:
			if subscribed.startswith('$share/'):
				await mqtt.unsubscribe(subscribed)


	async def __subscribe_required_listeners(self, mqtt):

		for listener in self.__listeners:

			if listener['state'] == SUBSTATE.TO_SUBSCRIBE:

				topic = self.__topic_for_listener_(listener)
				
				if not any(topic == s for s in self.__subscribed):
					print("MQTT: Subscribed to " + topic)
					await mqtt.subscribe(topic)
					self.__subscribed.append(topic)

				listener['state'] = SUBSTATE.SUBSCRIBED

	async def __unsubscribe_required_listeners(self, mqtt):

		for listener in self.__listeners:

			if listener['state'] == SUBSTATE.TO_UNSUBSCRIBE:
				topic = self.__topic_for_listener_(listener)

				listener['state'] = SUBSTATE.UNSUBSCRIBED
				#self.__listeners.remove(listener)


				found = False
				for check in self.__listeners:
					checktopic = self.__topic_for_listener_(check)
					if topic == checktopic and not (check['state']==SUBSTATE.TO_UNSUBSCRIBE or check['state']==SUBSTATE.UNSUBSCRIBED): 
						found = True

				if not found:
					if any(topic == s for s in self.__subscribed):
						print('MQTT: Unubscribed from '+ topic)
						await mqtt.unsubscribe(topic)
						self.__subscribed.remove(topic)



	async def __send_outgoing(self, mqtt):

		for outgoing in self.__outgoing:
			print("MQTT: Sending " + outgoing['topic'] + " \n" + outgoing['payload'])
			await mqtt.publish(outgoing['topic'], outgoing['payload'], retain=outgoing['retain'])

		self.__outgoing = []


	async def __recieve_incoming(self, mqtt):

		has_incoming = False
		has_perform = False

		if len(mqtt.messages) > 0:

			async for message in mqtt.messages:
				
				topic = str(message.topic)
				payload = message.payload
				print("MQTT: Recieved " + topic)

				# Addig to queue
				incomming = {'topic':topic, 'payload':payload}
				self.__incoming.append(incomming)
				has_incoming = True

				# Splitting
				topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts_(incomming)
				if action == 'perform': has_perform = True

				# Skipping for the next cycle
				#if len(mqtt.messages) == 0: raise aiomqtt.MqttError("Next") from None
				if len(mqtt.messages) == 0: break


		return has_incoming, has_perform

	def __incoming_parts_(self, incoming):

		topic = incoming['topic']
		payload = incoming['payload'] # bytes

		fulldata = self.__payload_to_fulldata_(payload)
		data = fulldata['data']

		splitted = topic.split('/')
		if len(splitted) > 4 :
			union = splitted[0]
			job = splitted[1]
			task = splitted[2]
			context = splitted[3]
			tid = splitted[4]
			#action = splitted[5] # Regulated by self.__action_in_topic
		else:
			union = ''
			job = ''
			task = ''
			context = ''
			tid = ''
			#action = ''

		if 'action' in fulldata:
			action = fulldata['action'] # Always so
		else:
			action = ''

		return topic, payload, fulldata, data, union, job, task, context, tid, action


	async def __for_message_fits_listener(self, incoming, callback):
		
		topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts_(incoming)

		if not task == '' and not action == '':

			if self.__union == union:
				for listener in self.__listeners:
					if listener['state'] != SUBSTATE.TO_UNSUBSCRIBE: # Important to remove this because of reply_incomming with UNSUBSCRIBED
						if listener['job'] == job and listener['task'] == task and listener['context'] == context and listener['action'] == action:
								

							# Checking tid (task id)
							if tid == listener['tid'] or action == 'perform': # there is no tid for 'perform' action

								await callback(incoming, listener)


	async def __reply_incoming_immediate(self):


		async def reply(incoming, listener):

			topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts_(incoming)

			if action == 'perform':
				# Sending immidiate message with progress == 0 to let know that we recieved the task
				await self.status(job, "", task, context, tid, {}, None, 0, immediate=False) # NOT immediate to send, using queue, as soon as we have a connection

			elif action == 'complete':
				pass
				# NO: This will avoid completion
				# We do not keep subscribing to complitance of this task
				#await self.dismiss(job, "", task, context, tid, {}, listener['handler'])



		for incoming in self.__incoming:
			await self.__for_message_fits_listener(incoming, reply)





	async def __process_incoming(self):


		async def handle(incoming, listener):

			topic, payload, fulldata, data, union, job, task, context, tid, action = self.__incoming_parts_(incoming)

			handler = listener['handler']
			if not handler is None:
				await handler(action, tid, data, fulldata)			



		for incoming in self.__incoming:
			await self.__for_message_fits_listener(incoming, handle)


		# Clearing all incoming
		self.__incoming = []



	async def __send_to_queue(self, job, workgroup, task, context, action, tid, payload, retain=False):

		topic = self.__union + '/' + job + '/' + task + '/' + context + '/' + tid
		if self.__action_in_topic: topic = topic + '/' + action
		 
		retain=False # Forsing NOT to retain
		self.__outgoing.append({'topic':topic, 'payload':payload, 'retain':retain})

	

	async def __send_immediate(self, job, workgroup, task, context, action, tid, payload, retain=False):

		topic = self.__union + '/' + job + '/' + task + '/' + context + '/' + tid
		if self.__action_in_topic: topic = topic + '/' + action
		 
		retain=False # Forsing NOT to retain

		# Connecting and sending
		#mqtt = await self.__new_mqtt()
		#async with mqtt:
		if self.__mqtt is not None:
			await self.__mqtt.publish(topic, payload, retain=retain)


	async def __send(self, job, workgroup, task, context, action, tid, payload, retain=False,  immediate=False):
		if immediate: await self.__send_immediate(job, workgroup, task, context, action, tid, payload, retain=retain)
		else:  await self.__send_to_queue(job, workgroup, task, context, action, tid, payload, retain=retain)



	async def idle(self, job, workgroup, task, context, tid, data, on_handle):
		if on_handle is not None: await self.subscribe(job, workgroup, task, context, tid, 'perform', on_handle)
		payload = self.__data_to_payload_('idle', 'online', 100, data)
		await self.__send(job, workgroup, task, context, 'idle', tid, payload, retain=False)


	async def perform(self, job, workgroup, task, context, tid, data, on_handle):
		if on_handle is not None: 
			await self.subscribe(job, workgroup, task, context, tid, 'status', on_handle)
			await self.subscribe(job, workgroup, task, context, tid, 'complete', on_handle)
		payload = self.__data_to_payload_('perform', 'initialized', 0, data)
		await self.__send(job, workgroup, task, context, 'perform', tid, payload, retain=True)


	async def complete(self, job, workgroup, task, context, tid, data, on_handle, success=True):
		result = 'succeed' if success else 'failed'
		payload = self.__data_to_payload_('complete', result, 100, data)
		await self.__send(job, workgroup, task, context, 'complete', tid, payload, retain=False)

	async def status(self, job, workgroup, task, context, tid, data, on_handle, progress=0, immediate=True):
		payload = self.__data_to_payload_('status', 'progress', progress, data)
		await self.__send(job, workgroup, task, context, 'status', tid, payload, retain=False, immediate=immediate)


	async def dismiss(self, job, workgroup, task, context, tid, data, on_handle):
		if on_handle is not None: await self.unsubscribe(job, workgroup, task, context, tid, 'complete', on_handle)
		payload = self.__data_to_payload_('dismiss', 'dismissed', 100, data)
		await self.__send(job, workgroup, task, context, 'dismiss', tid, payload, retain=False)


	async def online(self, job, workgroup, task, context, tid, data, on_handle):
		payload = self.__data_to_payload_('online', 'connected', 100, data)
		await self.__send(job, workgroup, task, context, 'online', tid, payload, retain=False)
		

	async def subscribe(self, job, workgroup, task, context, tid, action, handler_func):

		if not handler_func is None:

			self.__listeners.append({'job':job, 'workgroup':workgroup, 'task':task, 'context':context, 'tid':tid, 'action' : action, 'state' : SUBSTATE.TO_SUBSCRIBE, 'handler': handler_func})


	async def unsubscribe(self, job, workgroup, task, context, tid, action, handler_func):


		for listener in self.__listeners:
			if listener['job'] == job and listener['task'] == task and listener['context'] == context and listener['action'] == action and listener['handler'] == handler_func:				
				listener['state'] = SUBSTATE.TO_UNSUBSCRIBE



class aether(object):

	def __init__(self, instance, job, task, context="x", on_perform=None, on_status=None, on_complete=None, on_cancel=None):

		self.__instance = instance if instance is not None else AetherMagic.shared()
		self.__job = job
		self.__workgroup = 'workgroup'
		self.__task = task
		self.__context = context
		self.__tid = str(uuid1())[:8]

		self.__on_perform_func = on_perform
		self.__on_status_func = on_status
		self.__on_complete_func = on_complete
		self.__on_cancel_func = on_cancel

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		pass

	def __call__(self, querying_func):
		@wraps(querying_func)
		def inner(*args, **kwargs):
			with self:
				return querying_func(*args, **kwargs)
		return inner


	def wait_(self):
		async_to_sync(self.wait)()

	def perform_(self, data={}):
		async_to_sync(self.perform)(data)

	def status_(self, progress, data={}, immediate=False):
		async_to_sync(self.status)(progress, data, immediate)

	def complete_(self, success, data={}):
		async_to_sync(self.complete)(success, data)


	async def idle(self):
		if not self.__on_perform_func is None:  
			if not self.__instance is None:
				await self.__instance.idle(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, {}, self.on_handle)


	async def perform(self, data={}):
		if not self.__instance is None:
			await self.__instance.perform(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, data, self.on_handle)


	async def complete(self, success, data={}):
		if not self.__instance is None:
			await self.__instance.complete(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, data, None, success)


	async def status(self, progress, data={}, immediate=False):

		if progress < 0: progress = 0
		elif progress > 100: progress = 100

		if not self.__instance is None:
			await self.__instance.status(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, data, None, progress, immediate=immediate)


	async def on_handle(self, action, tid, data, fulldata):

		# Variables to use
		status = fulldata['status']
		succeed = True if status == 'succeed' else False
		failed = True if status == 'failed' else False
		complete = True if succeed or failed else False
		progress = fulldata['progress']


		callback_perform = None
		callback_complete = None
		callback_status = None
		callback_cancel = None

		if action == 'perform':

			callback_perform = self.__on_perform_func

			# if we are assigned to 'preform' action, we should reply with same tid.
			self.__tid = tid			


		elif action == 'status':			

			callback_status = self.__on_status_func

		elif action == 'complete':

			callback_status = self.__on_status_func
			callback_complete = self.__on_complete_func

		elif action == 'cancel':

			callback_cancel = self.__on_cancel_func



		if callback_perform is not None:
			if asyncio.iscoroutinefunction(callback_perform): await callback_perform(self, data)
			else: await sync_to_async(callback_perform)(self, data)

		if callback_status is not None:
			if asyncio.iscoroutinefunction(callback_status): await callback_status(self, complete, succeed, progress, data)
			else: await sync_to_async(callback_status)(self, complete, succeed, progress, data)

		if callback_complete is not None:
			if asyncio.iscoroutinefunction(callback_complete): await callback_complete(self, succeed, data)
			else: await sync_to_async(callback_complete)(self, succeed, data)

		if callback_cancel is not None:
			if asyncio.iscoroutinefunction(callback_cancel): await callback_cancel(self, data)
			else: await sync_to_async(callback_cancel)(self, data)




