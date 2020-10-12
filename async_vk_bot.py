from typing import Any, Coroutine
import vk_api
from vk_api.bot_longpoll import VkBotEvent, VkBotLongPoll, VkBotEventType, VkBotMessageEvent
import asyncio
import logging
from threading import Thread
import random
import functools
import types

from vk_api.vk_api import VkApiMethod
logging.basicConfig(level=logging.INFO)

USER = 0
CHAT = 1
GROUP = 2
ME = 3
CHAT_PEER_ID = 4
USER_PEER_ID = 5

STAGE_WRITING_EVENT_HANDLERS = 0
STAGE_LOOPING_PROGRAMM = 1
programm_stage =STAGE_WRITING_EVENT_HANDLERS
handlers = {
    "on_message": [],
    "on_command": []
}

# BASE_HANDLER = 8
# ON_MESSAGE_HANDLER = 9

# programm_stage =STAGE_WRITING_EVENT_HANDLERS
# class Handler:
#     def __init__(self):
#         self.handler_type = BASE_HANDLER
#     def decorator():
#         pass
# class OnMessageHandler(Handler):
#     def __init__(self, func, from_chat=False, from_group=False, from_user=False, pass_event=False):
#         super().__init__()
#         self.from_chat = from_chat
#         self.from_group = from_group
#         self.from_user = from_user
#         self.pass_event = pass_event
#         self.handler_type = ON_MESSAGE_HANDLER
#     def decorator(func):
#         async def wrapper(event):
#             if self.fro
#             func(event)
        
# class Handlers:
#     def __init__(self) -> None:
#         self.on_message_from_chat = []
#         self.on_message_from_group = []
#         self.on_message_form_user = []
#     def add(self, func, from_chat=False, from_group=False, from_user=False):
#         if from_chat:
#             self.on_message_from_chat.append(func)
#         if from_group:
#             self.on_message_from_group.append(func)
#         if from_user:
#             self.on_message_form_user.append(func)
#     def execute_handlers(self, event: VkBotMessageEvent):
#         executed = []
#         for func in self.on_message_form_chat:
#             func(event)

class Bot:
    def __init__(self, token, group_id, longpoll_api_version='5.124') -> None:
        if longpoll_api_version != '5.124': raise AssertionError("Longpoll api version must be 5.124")
        self.group_id = group_id
        self.event_loop = asyncio.get_event_loop()
        self.vk_session = vk_api.VkApi(token=token)
        self.vk: VkApiMethod = self.vk_session.get_api()
        self.tasks_to_add = []
    def _on_message(self, from_user: bool = False, from_chat: bool = False, 
        from_group: bool = False, from_me:bool = False):
        def on_message_decorator(func):
            # @functools.wraps(func)
            async def wrapper(event, *args) -> Any:
                if (from_user and event.from_user) or\
                (from_chat and event.from_chat) or\
                (from_group and event.from_group) or\
                (from_me and event.from_me):
                    return await func(event, *args)
            return wrapper
        return on_message_decorator
    def on_message(self, from_user: bool = False, from_chat: bool = False, 
        from_group: bool = False, from_me:bool = False):
        def on_message_decorator(func):
            handlers["on_message"].append(Bot._on_message(Bot, from_user, from_chat, from_group, from_me)(func))
        return on_message_decorator
    async def get_random_id(self):
        return random.getrandbits(31) * random.choice([-1, 1])
    async def send(self, chat_type, user_id=None, chat_id=None, peer_id=None, **kwargs):
        if chat_type == USER:
            self.vk.messages.send(user_id=user_id, random_id=await self.get_random_id(), **kwargs)
        elif chat_type == CHAT:
            self.vk.messages.send(chat_id=chat_id, random_id=await self.get_random_id(),  **kwargs)
        elif chat_type == CHAT_PEER_ID:
            self.vk.messages.send(peer_id=peer_id, random_id=await self.get_random_id(),  **kwargs)
        elif chat_type == USER_PEER_ID:
            self.vk.messages.send(peer_id=peer_id, random_id=await self.get_random_id(),  **kwargs)
    async def task_manager(self, interval=0.1, ingnore_not_coro_tasks=True):
        while(True):
            if len(self.tasks_to_add) > 0:
                if ingnore_not_coro_tasks:
                    if type(self.tasks_to_add[0]) is not types.CoroutineType:
                        logging.warning("Skipping not coroutine task in task manager!")
                        break
                try: self.event_loop.create_task(self.tasks_to_add[0])
                except: logging.error("Error in task manager: Creationg CORO error")
                self.tasks_to_add.pop(0)
            await asyncio.sleep(interval)

    def listen(self):
        longpoll = VkBotLongPoll(self.vk_session, self.group_id, wait=False)
        crached = False
        while(True):
            try:
                if crached:
                    logging.info("Listening restarted!")
                    crached = False
                for event in longpoll.listen():
                    # evattr = EventAttributeGetter(event)
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        logging.info("New message: " + event.message.text)
                        for coro in handlers["on_message"]:
                            self.tasks_to_add.append(coro(event))
            except Exception as err:
                logging.error(f"Error {err.args} in listening loop. Restarting...")
                crached = True
    
    def run(self):
        logging.info("Starting listen thread")
        Thread(name="listener", target=self.listen).start()
        logging.info("Running event loop forever")
        programm_stage = STAGE_LOOPING_PROGRAMM
        self.event_loop.create_task(self.task_manager())
        self.event_loop.run_forever()