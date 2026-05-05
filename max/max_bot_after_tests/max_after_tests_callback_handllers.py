from maxapi.enums.upload_type import UploadType
from maxapi.types import MessageCallback, InputMediaBuffer
from pathlib import Path
from db.after_tests import after_tests_db
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_go_to_main_menu
from max.max_bot_after_tests.max_bot_after_tests_main_menu import after_tests_main_menu
from resources import text_about_doctor
from utils.after_tests_utils import write_and_sleep

image_path = Path(__file__).parent.parent.parent / "images" / "TVH.jpg"

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

async def handle_get_doctor_info(event: MessageCallback):
    chat_id, user_id = event.get_ids()
    with open(image_path, "rb") as image_file:
        buffer = image_file.read()  # читаем весь файл в память
        media = InputMediaBuffer(buffer=buffer, filename="TVH.jpg", type=UploadType.IMAGE)

        await event.bot.send_message(
            chat_id = chat_id,
            text= text_about_doctor,
            attachments=[media, kb_go_to_main_menu()]
            )
