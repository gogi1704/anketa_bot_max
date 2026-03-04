import os
import logging
from dotenv import load_dotenv
from db.after_tests import after_tests_db
from max.max_bot_anamnez.max_bot_chat_manager import handle_reply_button_pressed, handle_manager_reply
from utils.util_fins import context_manager

from maxapi import Dispatcher
from maxapi.types import (
    Command, BotCommand, )


from max.max_bot_anamnez.max_bot_navigation import *
from ai_agents.open_ai_main import get_gpt_answer

load_dotenv()
TOKEN = os.environ.get("MAX_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()







@dp.message_callback()
async def callback_router(event: MessageCallback):
    chat_id, user_id = event.get_ids()
    payload = event.callback.payload

    # Закрываем "loading" кнопки
    await event.answer()

    # ===== CONSENT =====
    if payload in ("consent_yes", "consent_no"):
        await handle_consent(event, payload)
        return

    # ===== TOGGLE =====
    if payload.startswith("toggle:") or payload == "done":
        await handle_toggle(event, context_manager.get(chat_id, user_id))
        return

    # ===== DOP =====
    if payload.startswith("dop_"):
        await handle_dop_analizy(event, context_manager.get(chat_id, user_id))
        return

    if payload.startswith("dopDop_"):
        await handle_dopDop_analizy(event,context_manager.get(chat_id, user_id))
        return

    # ===== MANAGER REPLY =====
    if payload.startswith("reply_to_manager|"):
        await handle_reply_button_pressed(event)
        return

@dp.bot_started()
async def bot_started_handler(event: BotStarted):
    await bot_started(event)

@dp.message_created(Command("start"))
async def start_handler(event: MessageCreated):
    await start(event)


# @dp.message_created(Command("update_db"))
# async def update_db_handler(event: MessageCreated):
#     await update_db(event)


@dp.message_created(Command("clear_and_restart"))
async def clear_handler(event: MessageCreated):
    await clear_all(event, bot)


@dp.message_created()
async def text_handler(event: MessageCreated):
    text = event.message.body.text

    if not text:
        return

    if event.message.link and event.message.link.chat_id == resources.GROUP_CHAT_ID:
        await handle_manager_reply(event)
        return
    elif event.message.recipient.chat_id == resources.GROUP_CHAT_ID:
        await handle_manager_reply(event)
        return



    await handle_text_message(event)


async def main():
    await anamnez_db.init_db()
    await after_tests_db.init_db()

    asyncio.create_task(after_tests_db.periodic_sync(interval= 4000))
    asyncio.create_task(anamnez_db.periodic_sync())

    # прогрев GPT
    await get_gpt_answer("test", "test", bot=bot)

    print("MAX бот запущен...")

    try:
        await bot.set_my_commands(BotCommand(name= "start", description= "Старт"))
        await bot.get_updates(marker=0)
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception("Ошибка polling: %s", e)


if __name__ == "__main__":
    asyncio.run(main())
