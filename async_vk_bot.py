import json
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
listeners = {
    "on_message": [],
}
user_commands = {}
conversation_commands = {}
async def get_user_commands_names():
    commands_names = []
    for user_command_name in user_commands:
        commands_names.append(user_command_name.replace(r"\l", ""))
    return commands_names
async def get_conversation_commands_names():
    commands_names = []
    for conversation_command_name in conversation_commands:
        commands_names.append(conversation_command_name.replace(r"\l", ""))
    return commands_names

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
        """`|Декоратор для корутины|`\n
        Слушатель сообщений. Активирует корутину при входящем сообщении
        """
        def on_message_decorator(func):
            listeners["on_message"].append(Bot._on_message(
                Bot, from_user, from_chat, from_group, from_me)(func))
        return on_message_decorator
 
    def command(self, conversation: bool=True, user: bool=True, command_name: bool=None, do_lower_symbs: bool=True): 
        """`|Декоратор для корутины|`\n
        При получении сообщения, начинающегося с `command_name` срабатывает декорируемая корутина. На одно название команды может приходиться не более двух разных корутин - для пользователей и для сообществ\n
        - `conversation: bool` - будет ли срабатывать корутина при получении сообщения в беседе
        - `user: bool` - будет ли срабатывать корутина при получении сообщения от пользователя
        - `command_name: str {опционально}` - название команды. Опциональный аргумент. При отсутствии используется имя корутины
        - `do_lower_symbs: bool {опционально}` - конвертация букв в строчной регистр
        """
        def command_decorator(func):
            if command_name is None:
                out_name = func.__name__
            else:
                out_name = command_name
            if do_lower_symbs:
                out_name: str = r"\l{}".format(out_name.lower())
            if conversation:
                conversation_commands.update({out_name: func})
            if user:
                user_commands.update({out_name: func})
        return command_decorator

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

    async def send_user(self, user_id=None, **kwargs):
        await self.send(USER, user_id=user_id, **kwargs)

    async def send_chat(self, peer_id=None, **kwargs):
        await self.send(CHAT_PEER_ID, peer_id=peer_id, **kwargs)

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
    def _get_command_and_add_to_tasks(self, command, event):
        if user_commands.get(command, False) != False:
            self.tasks_to_add.append(user_commands[command](event))
            return True
        elif conversation_commands.get(command, False) != False:
            self.tasks_to_add.append(conversation_commands[command](event))
            return True
        return False
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
                        for coro in listeners["on_message"]:
                            self.tasks_to_add.append(coro(event))
                        if event.from_user or event.message.text[0] == self.prefix:
                            if event.message.text[0] == self.prefix: 
                                command = event.message.text.split()[0][1:]
                            else:
                                command = event.message.text.split()[0]
                            if not self._get_command_and_add_to_tasks(command, event):
                                self._get_command_and_add_to_tasks(r"\l{}".format(command.lower()), event)
            except Exception as err:
                logging.error(  
                    f"Error {err.args} in listening loop. Restarting...")
                crached = True

    def run(self):
        """Запуск бота. Бесконечный цикл"""
        logging.info("Starting listen thread")
        Thread(name="listener", target=self.listen).start()
        logging.info("Running event loop forever")
        programm_stage = STAGE_LOOPING_PROGRAMM
        self.event_loop.create_task(self.task_manager())
        self.event_loop.run_forever()

# if __name__ == '__main__':
#     with open("credentials.json",'r') as file:
#         loads = json.loads(file.read())
#     bot = Bot(loads["token"], loads["group_id"], log_input_messages=True)
#     @bot.on_message(from_user=True)
#     async def on_message(event: VkBotMessageEvent):
#         user_cmds_names = await get_user_commands_names()
#         if event.message.text not in user_cmds_names and event.message.text.lower not in user_cmds_names:
#             await bot.send_user(event.message.from_id, message="Я не нашёл такой команды(")
#     @bot.command(user=True, conversation=False)
#     async def help(event: VkBotMessageEvent):
#         await bot.send_user(event.message.from_id, message="Помощь)")
#     bot.run()
