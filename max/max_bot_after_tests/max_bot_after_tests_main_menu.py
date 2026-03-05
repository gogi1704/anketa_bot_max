from maxapi.types import MessageCallback
import resources
from max.max_bot_after_tests.max_after_tests_keyboards import tests_keyboards
from db.after_tests import after_tests_db as db


async def after_tests_main_menu(event):
    chat_id,user_id = event.get_ids()
    user_state = await db.get_user_state(user_id)
    if user_state is None:
        await db.set_user_state(telegram_id= user_id , user_state= "MAX")


    await event.bot.send_message(
        chat_id=chat_id,
        text=resources.TEXT_TESTS_MAIN_MENU,
        attachments=[tests_keyboards.kb_tests_main_menu()]
    )