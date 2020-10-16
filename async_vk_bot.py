import re
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
programm_stage = STAGE_WRITING_EVENT_HANDLERS
handlers = {
    "on_message": [],
}
user_commands = {}
conversation_commands = {}

class Bot:
    def __init__(self, token, group_id, prefix='.', longpoll_api_version='5.124', longpoll_wait=False, log_input_messages=True) -> None:
        if longpoll_api_version != '5.124':
            raise AssertionError("Longpoll api version must be 5.124")
        self.group_id = group_id
        self.longpoll_wait = longpoll_wait
        self.log_input_messages = log_input_messages
        self.event_loop = asyncio.get_event_loop()
        self.vk_session = vk_api.VkApi(token=token)
        self.vk: VkApiMethod = self.vk_session.get_api()
        self.prefix = prefix
        self.tasks_to_add = []

    def _on_message(self, from_user: bool = False, from_chat: bool = False,
                    from_group: bool = False, from_me: bool = False):
        def on_message_decorator(func):
            # @functools.wraps(func)
            async def wrapper(event, *args) -> Any:
                if (from_user and event.from_user) or\
                    (from_chat and event.from_chat) or\
                    (from_group and event.from_group) or\
                        (from_me and event.from_me):
                    await func(event, *args)
            return wrapper
        return on_message_decorator

    def on_message(self, from_user: bool = False, from_chat: bool = False,
                   from_group: bool = False, from_me: bool = False):
        def on_message_decorator(func):
            handlers["on_message"].append(Bot._on_message(
                Bot, from_user, from_chat, from_group, from_me)(func))
        return on_message_decorator

    # def command(self, conversation: bool=True, user: bool=True, command_name=None):
    #     def command_decorator(func):
    #         if command_name is None:
    #             out_name = func.__name__
    #         else:
    #             out_name = command_name
    #         if conversation:
    #             conversation_commands.update({out_name: func})
    #         if user:
    #             user_commands.update({out_name: func})
    #     return command_decorator

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
                        logging.warning(
                            "Skipping not coroutine task in task manager!")
                        break
                try:
                    self.event_loop.create_task(self.tasks_to_add[0])
                except:
                    logging.error(
                        "Error in task manager: Creationg CORO error")
                self.tasks_to_add.pop(0)
            await asyncio.sleep(interval)

    def listen(self):
        longpoll = VkBotLongPoll(self.vk_session, self.group_id)
        crached = False
        while(True):
            try:
                if crached:
                    logging.info("Listening restarted!")
                    crached = False
                for event in longpoll.listen():
                    # evattr = EventAttributeGetter(event)
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        if self.log_input_messages:
                            logging.info("New message: " + event.message.text)
                        for coro in handlers["on_message"]:
                            self.tasks_to_add.append(coro(event))
                        # if event.from_user or event.message.text[0] == self.prefix:
                        #     if event.message.text[0] == self.prefix: 
                        #         command = event.message.text.split()[0][1:]
                        #     else:
                        #         command = event.message.text.split()[0]
                        #     if user_commands.get(command, False) != False:
                        #         self.tasks_to_add.append(user_commands[command](event))
                        #     elif conversation_commands.get(command, False) != False:
                        #         self.tasks_to_add.append(conversation_commands[command](event))

            except Exception as err:
                logging.error(
                    f"Error {err.args} in listening loop. Restarting...")
                crached = True

    def run(self):
        logging.info("Starting listen thread")
        Thread(name="listener", target=self.listen).start()
        logging.info("Running event loop forever")
        programm_stage = STAGE_LOOPING_PROGRAMM
        self.event_loop.create_task(self.task_manager())
        self.event_loop.run_forever()

# if __name__ == '__main__':
#     bot = Bot("fe6d6669cbe000cfc33b1a7e2187e3cf0b854e39bcbf3b479b4b1320346b307be53345ac4f3c2d4586111", 199402229, log_input_messages=False)
#     @bot.command(user=True, conversation=False)
#     async def help(event: VkBotMessageEvent):
#         bot.send(USER, user_id=eval.message.from_id, message="помощь")
#     bot.run()
