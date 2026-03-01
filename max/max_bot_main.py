import os
import asyncio
import logging
import datetime
from dotenv import load_dotenv
from db.dialogs_db import  periodic_sync
from max.max_bot_chat_manager import handle_reply_button_pressed, handle_manager_reply
from utils.util_fins import context_manager

from maxapi import Bot, Dispatcher
from maxapi.types import (
    MessageCreated,
    MessageCallback,
    Command, BotCommand, BotStarted,
)


from max.max_bot_navigation import *
# from tg.tg_bot_util_handlers import update_db
# from tg.tg_manager_chat_handlers import *
# from tg.tg_bot_channel_funs import *
# from tg.tg_error_handlers import error_handler
from db import dialogs_db
from ai_agents.open_ai_main import get_gpt_answer

load_dotenv()
TOKEN = os.environ.get("MAX_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()




async def handle_consent(event: MessageCallback, payload: str):
    chat_id, user_id = event.get_ids()

    user_data = await dialogs_db.get_user(user_id=user_id)

    if payload == "consent_yes":
        await dialogs_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["get_number"]
        )

        await dialogs_db.add_user(
            user_id=user_id,
            name=user_data['name'],
            is_medosomotr=user_data['is_medosomotr'],
            phone=user_data["phone"],
            register_date=user_data['register_date'],
            from_manager="from_manager",
            privacy_policy_date=datetime.datetime.now(datetime.UTC),
        )

        await dialogs_db.append_answer(
            telegram_id=user_id,
            text=f"Менеджер сказал: {resources.get_number_text}"
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.privacy_policy_true
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.get_number_text
        )

    elif payload == "consent_no":
        await dialogs_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_state"]
        )

        await dialogs_db.add_user(
            user_id=user_id,
            name=user_data['name'],
            is_medosomotr=user_data['is_medosomotr'],
            phone=user_data["phone"],
            register_date=user_data['register_date'],
            from_manager="from_manager",
            privacy_policy_date=datetime.datetime.now(datetime.UTC),
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.privacy_policy_false
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text="Спасибо за ответы. До встречи на медосмотре!"
        )


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

# =============================
# COMMANDS
# =============================

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


# @dp.message_created(Command("stop_privacy"))
# async def stop_privacy_handler(event: MessageCreated):
#     await stop_privacy(event)


# =============================
# TEXT HANDLER
# =============================

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


# =============================
# MAIN
# =============================

async def main():
    await dialogs_db.init_db()
    asyncio.create_task(periodic_sync())

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
