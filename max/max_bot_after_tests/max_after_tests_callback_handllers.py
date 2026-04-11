from maxapi.types import MessageCallback

from db.after_tests import after_tests_db
from max.max_bot_after_tests.max_bot_after_tests_main_menu import after_tests_main_menu
from utils.after_tests_utils import write_and_sleep


async def handle_get_your_sex(event: MessageCallback):
    chat_id, user_id = event.get_ids()
    payload = event.callback.payload

    if payload == "get_your_sex_man":
        await after_tests_db.set_user_sex(user_id=user_id, user_name="Мужчина")
    elif payload == "get_your_sex_woman":
        await after_tests_db.set_user_sex(user_id=user_id, user_name="Женщина")
    await event.bot.send_message(chat_id = chat_id,
                                 text= "Спасибо за ответ.")
    await write_and_sleep(event, chat_id, 1)

    await after_tests_main_menu(event)