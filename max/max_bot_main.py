import os
import logging
from dotenv import load_dotenv
from db.db_utils import update_db
from max.max_bot_after_tests.max_after_tests_callback_handllers import handle_get_your_sex
from max.max_bot_chat.max_bot_chat_manager import handle_reply_button_pressed, handle_manager_reply
from max.max_bot_chat import max_bot_cha_manager_after_tests
from utils.after_tests_utils import scheduler
from utils.util_fins import context_manager
from max.max_bot_after_tests.max_bot_after_tests_main_menu import handle_after_tests_main_menu, handle_start_check_up, \
    handle_decode_yes_no, handle_after_good_tests_yes_no, after_tests_main_menu, handle_empty_decode
from maxapi import Dispatcher, Bot
from maxapi.types import (
    Command, BotCommand, )
from max.max_bot_after_tests.max_util_handlers import get_statistic_by_inn, get_statistic_inn_by_date, \
    get_dop_tests_statistic
from max.max_bot_after_tests.max_text_hanlers import handle_text_message_after_tests
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

    user_data = await anamnez_db.get_user(user_id)
    anketa = await  anamnez_db.get_anketa(user_id)
    age = 0
    name = "Не заполнено"
    if anketa:
        age = anketa["age"] if anketa["age"] else 0
    if user_data:
        name = user_data["name"] if user_data["name"] else "Не заполнено"

    # Закрываем "loading" кнопки
    # await event.answer()
#__________________________________________________________________________________________________
    # ===== CONSENT =====
    if payload in ("consent_yes", "consent_no"):
        await handle_consent(event, payload)
        return

    # ===== TOGGLE =====
    if payload.startswith("toggle:") or payload == "done" or payload == "skip_tests":
        is_after_tests =  await handle_toggle(event, context_manager.get(chat_id, user_id))
        if is_after_tests:
            await after_tests_main_menu(event)
        return

    # ===== DOP =====
    if payload.startswith("dop_"):
        await handle_dop_analizy(event, context_manager.get(chat_id, user_id))
        return

    if payload.startswith("dopDop_"):
        is_after_tests = await handle_dopDop_analizy(event, context_manager.get(chat_id, user_id))
        if is_after_tests:
            await after_tests_main_menu(event)
        return

#__________________________________________________________________________________________________

    if payload.startswith("tests_main_menu_"):
        await handle_after_tests_main_menu(event, name, age)
        return

    if payload.startswith("сheck_up_start_"):
        await handle_start_check_up(event,context_manager.get(chat_id, user_id))
        return

    if payload.startswith("tests_decode_"):
        await handle_decode_yes_no(event, name, age)
        return

    if payload.startswith("after_good_tests_"):
        await handle_after_good_tests_yes_no(event)
        return

    if payload.startswith("empty_decode_get_"):
        await handle_empty_decode(event)
        return

    if payload.startswith("go_to_main_menu"):
        await after_tests_main_menu(event)
        return

    if payload.startswith("pay"):
        await handle_pay(event)

    if payload.startswith("get_your_sex_"):
        await handle_get_your_sex(event)


# __________________________________________________________________________________________________

    # ===== MANAGER REPLY =====
    if payload.startswith("reply_to_manager|"):
        chat_id, user_id = event.get_ids()
        user_is_after_tests = await after_tests_db.get_user_state(user_id)

        if user_is_after_tests:
            await max_bot_cha_manager_after_tests.handle_reply_button_pressed(event)
        else:
            await handle_reply_button_pressed(event)
        return

@dp.bot_started()
async def bot_started_handler(event: BotStarted):
    chat_id, user_id = event.get_ids()
    user_is_after_tests = await after_tests_db.get_user_state(user_id)
    if user_is_after_tests:
        await after_tests_main_menu(event)
    else:
        ref_code = await bot_started(event)
        if ref_code:
            await after_tests_main_menu(event)

@dp.message_created(Command("start"))
async def start_handler(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    user_is_after_tests = await after_tests_db.get_user_state(user_id)

    if user_is_after_tests:
        await after_tests_main_menu(event)
    else:
        await start(event)


@dp.message_created(Command("update_db"))
async def update_db_handler(event: MessageCreated):
    await update_db(event)


@dp.message_created(Command("clear_and_restart"))
async def clear_handler(event: MessageCreated):
    await clear_all(event)

@dp.message_created(Command("get_stat_inn"))
async def get_stat_inn(event: MessageCreated):
    await get_statistic_by_inn(event)

@dp.message_created(Command("get_stat_inn_by_date"))
async def get_stat_inn_by_date(event: MessageCreated):
    await get_statistic_inn_by_date(event)

@dp.message_created(Command("get_dop_tests_stat"))
async def get_dop_tests_stat(event: MessageCreated):
    await get_dop_tests_statistic(event)

@dp.message_created()
async def text_handler(event: MessageCreated):
    text = event.message.body.text
    chat_id, user_id = event.get_ids()
    user_is_after_tests= await after_tests_db.get_user_state(user_id)

    if not text:
        return

    if event.message.link and event.message.link.chat_id == resources.GROUP_CHAT_ID:
        if user_is_after_tests:
            await max_bot_cha_manager_after_tests.handle_manager_reply(event)
        else:
            await handle_manager_reply(event)
        return

    elif event.message.recipient.chat_id == resources.GROUP_CHAT_ID:
        if user_is_after_tests:
            await max_bot_cha_manager_after_tests.handle_manager_reply(event)
        else:
            await handle_manager_reply(event)
        return

    if user_is_after_tests:
        await handle_text_message_after_tests(event)
        return

    await handle_text_message_anamnez(event, context_manager.get(chat_id, user_id))


async def main():
    await anamnez_db.init_db()
    await after_tests_db.init_db()

    asyncio.create_task(after_tests_db.periodic_sync(interval= 4000))
    asyncio.create_task(anamnez_db.periodic_sync())
    asyncio.create_task(scheduler(bot))

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
