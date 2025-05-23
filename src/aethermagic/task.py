
from uuid import uuid1

#from functools import wraps

import asyncio
from asyncio import Queue
from asgiref.sync import async_to_sync, sync_to_async

from .magic import AetherMagic

class AetherTask():

    def __init__(self, job, task, context="x", on_perform=None, on_status=None, on_complete=None, on_cancel=None):

        self.__instance = AetherMagic.shared()
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

    def copy(self, tid=''):
        ae_copy = AetherTask(
            job=self.__job,
            task=self.__task,
            context=self.__context,
            on_perform=self.__on_perform_func,
            on_status=self.__on_status_func,
            on_complete=self.__on_complete_func,
            on_cancel=self.__on_cancel_func
        )

        # Copying tid (or setting new)
        if tid: ae_copy.tid_(tid)
        else: ae_copy.tid_(self.__tid)

        return ae_copy

#	def __call__(self, querying_func):
#		@wraps(querying_func)
#		def inner(*args, **kwargs):
#			with self:
#				return querying_func(*args, **kwargs)
#		return inner


    def tid_(self, tid=''):
        if tid: self.__tid = tid
        return self.__tid

    def idle_(self):
        return async_to_sync(self.idle)()

    def perform_(self, data={}):
        return async_to_sync(self.perform)(data)

    def status_(self, progress, data={}, immediate=False):
        return async_to_sync(self.status)(progress, data, immediate)

    def complete_(self, success, data={}):
        return async_to_sync(self.complete)(success, data)


    async def tid(self, tid=''):
        if tid: self.__tid = tid
        return self.__tid

    async def idle(self, immediate=False):
        if not self.__on_perform_func is None:  
            if not self.__instance is None:
                await self.__instance.idle(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, {}, self.on_handle, immediate=immediate)

        return self.__tid


    async def perform(self, data={}, immediate=False):
        if not self.__instance is None:
            await self.__instance.perform(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, data, self.on_handle, immediate=immediate)

        return self.__tid


    async def complete(self, success, data={}, immediate=False):
        if not self.__instance is None:
            await self.__instance.complete(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, data, None, success, immediate=immediate)

        return self.__tid


    async def status(self, progress, data={}, immediate=False):

        if progress < 0: progress = 0
        elif progress > 100: progress = 100

        if not self.__instance is None:
            await self.__instance.status(self.__job, self.__workgroup, self.__task, self.__context, self.__tid, data, None, progress, immediate=immediate)

        return self.__tid


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

        # AetherTask to send to handle functions
        ae_task = self

        if action == 'perform':

            callback_perform = self.__on_perform_func

            # if we are assigned to 'preform' action, we should reply with same tid.
            ae_task = self.copy(tid)


        elif action == 'status':			

            callback_status = self.__on_status_func

        elif action == 'complete':

            callback_status = self.__on_status_func
            callback_complete = self.__on_complete_func

        elif action == 'cancel':

            callback_cancel = self.__on_cancel_func



        if callback_perform is not None:
            asyncio.create_task(callback_perform(ae_task, data))

        if callback_status is not None:
            asyncio.create_task(callback_status(ae_task, complete, succeed, progress, data))

        if callback_complete is not None:
            asyncio.create_task(callback_complete(ae_task, succeed, data))

        if callback_cancel is not None:
            asyncio.create_task(callback_cancel(ae_task, data))

