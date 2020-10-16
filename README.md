# async-vk-bot
Простая асинхронная библиотека, использующая механизмы стандартной библиотеки vk_api
## Зависимости (requirements)
* vk_api
## Использование
Для создания бота необзодимо вызвать базовый класс Bot:
```python
bot = async_vk_bot.Bot(токен, id-сообщества)
```
Далее, необходимо добавить асинхронные слушатели (больше в будущем):
```python
@bot.on_message(Параметры слушателя) #слушатель входящего сообщения
async def on_message(event: VkBotMessageEvent):
  pass
```
Параметры слушателя:
* from_user (bool) - будет ли слушатель реагировать на сообщение от пользователя
* from_chat (bool) - будет ли слушатель реагировать на сообщение из чата 
* from_group (bool) - будет ли слушатель реагировать на сообщение от группы
* from_me (bool) - будет ли слушатель реагировать на сообщение от самого себя

И, наконец, запуск бота:
```python
bot.run()
```
Для отправки сообщений используйте асинхронный метод класса Bot.
Так, как в вк разные механизмы для отправки пользователям и в беседы, то нужно использовать разные методы.
Отправка в беседу:
```python
await bot.send_chat(peer_id=event.message.peer_id, message="сообщение")
```
Отправка пользователю:
```python
await bot.send_user(user_id=event.message.from_id, message="сообщение")
```
