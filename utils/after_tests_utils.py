import asyncio
import html
import json

from maxapi import Bot
from maxapi.enums.sender_action import SenderAction
from maxapi.methods.types.sended_message import SendedMessage

from db.after_tests import after_tests_db as data_base
from db.after_tests.after_tests_db import sync_tests_job
from max.max_bot_chat.max_bot_chat_manager import send_to_chat


def parse_base_answer(model_response: str) -> str:
    """
    Извлекает значение поля 'answer' из JSON-ответа модели.
    Возвращает строку answer или выбрасывает исключение при ошибке.
    """
    try:
        data = json.loads(model_response)
        answer = data.get("answer")

        if answer is None:
            raise ValueError("Поле 'answer' отсутствует в ответе модели")

        return answer

    except json.JSONDecodeError as e:
        raise ValueError(f"Ответ модели не является валидным JSON: {e}. \n\n Ответ модели: {model_response}")

def pars_answer_and_data(model_response: str) :
    """
    Извлекает значение поля 'answer' из JSON-ответа модели.
    Возвращает строку answer или выбрасывает исключение при ошибке.
    """
    try:
        data = json.loads(model_response)
        answer = data.get("answer")
        user_data = data.get("data")
        if answer is None:
            raise ValueError("Поле 'answer' отсутствует в ответе модели")

        return answer, user_data

    except json.JSONDecodeError as e:
        raise ValueError(f"Ответ модели не является валидным JSON: {e}. \n\n Ответ модели: {model_response}")

async def write_and_sleep(event, chat_id,  sleep_time):
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )
    await asyncio.sleep(sleep_time)

def parse_int(text: str) -> int | None:
        try:
            return int(text)
        except ValueError:
            return None

async def send_wait_emoji(bot:Bot, chat_id: int, wait_text: str = "⏳"):
    try:
        return await bot.send_message(chat_id=chat_id, text=wait_text)
    except Exception:
        return None

async def replace_wait_with_text(bot:Bot, chat_id: int, wait_msg:SendedMessage, answer_text: str):

    if wait_msg and getattr(wait_msg.message.body, "mid", None):
        try:
            await bot.edit_message(
                message_id=wait_msg.message.body.mid,
                text=answer_text
            )
            return
        except Exception:
            try:
                await bot.delete_message(
                    message_id=wait_msg.message.body.mid
                )
            except Exception:
                pass

    # fallback
    await bot.send_message(chat_id=chat_id, text=answer_text)



_pending_decode_lock = asyncio.Lock()

async def process_pending_kind(bot:Bot, kind: str):

    kind = str(kind).strip().lower()
    tasks = await data_base.get_all_pending_by_kind(kind)

    MAX_PER_RUN = 300
    sent = 0
    for row_id, med_id, telegram_id, chat_id in tasks:

        if sent >= MAX_PER_RUN:
            break

        if kind == "decode":

            result = await data_base.get_results_only(med_id)
            if not result or not str(result).strip():
                continue

            decode = await data_base.get_decode_only(med_id)
            if not decode or not str(decode).strip():
                decode = "Пока нет расшифровки результатов."

            text = (
                f"Вот результаты ваших анализов:\n{result}\n\n"
                f"Расшифровка:\n{decode}"
            )

            try:
                await bot.send_message(chat_id=chat_id, text=text)
                await data_base.delete_pending_by_id(row_id)
                message_text = f"Пользователь оставлял заявку на получение консультации по результатам анализов. Только что мы отправили ему результаты.\n({result})\n \n\n#Диалог_{telegram_id}"
                await send_to_chat(bot= bot, user_id= telegram_id, message_text= message_text )
                sent += 1
                await asyncio.sleep(0.2)

            except Exception as e:
                print(f"[ERR] sending decode med_id={med_id} chat_id={chat_id}: {e}")
                continue


async def pending_decode_job(bot:Bot):
    if _pending_decode_lock.locked():
        return

    async with _pending_decode_lock:
        await process_pending_kind(bot, "decode")


async def scheduler(bot:Bot):
    while True:
        await sync_tests_job()
        await pending_decode_job(bot)
        await asyncio.sleep(7200)  # каждые 2 часа

# def setup_jobs(application):
#     application.job_queue.run_repeating(
#         pending_decode_job,
#         interval=timedelta(minutes=120),
#         first=1800,
#         name="pending_decode_job"
#     )
#
#     application.job_queue.run_repeating(
#         data_base.sync_tests_job,
#         interval=timedelta(minutes=180),
#         first=3600,
#         name="sync_tests_job"
#     )
#
#     print("[DEBUG] jobs:", [j.name for j in application.job_queue.jobs()])

def bold_html(text: str) -> str:
    """
    Экранирует текст для HTML и оборачивает его в <b>...</b>
    """
    safe_text = html.escape(text)
    return f"<b>{safe_text}</b>"

async def get_list_and_price(list_tests,tests_price ):
    text = ""
    price = 0
    for test in list_tests:
        text += f"{test} - {tests_price[test]}₽\n"
        price += tests_price[test]

    return text, price