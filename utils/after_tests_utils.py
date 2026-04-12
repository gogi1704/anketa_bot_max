import asyncio
import html
import json

from maxapi import Bot
from maxapi.enums.sender_action import SenderAction
from maxapi.methods.types.sended_message import SendedMessage
from ai_agents import check_tests_pdf
from db.after_tests import after_tests_db
from doc_funs import split_urls_from_cell
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_go_to_main_menu
from max.max_bot_chat.max_bot_chat_manager import send_to_chat
from db.anamnez import anamnez_db


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
            answer_text = f"{answer_text}\n\n\n<<Для ответа отправьте текстовое сообщение или воспользуйтесь кнопкой для возврата в главное меню>>"
            await bot.edit_message(
                message_id=wait_msg.message.body.mid,
                text=answer_text,
                attachments= [kb_go_to_main_menu()]
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
    await bot.send_message(chat_id=chat_id, text=answer_text,attachments= [kb_go_to_main_menu()])



_pending_decode_lock = asyncio.Lock()

async def process_pending_kind(bot:Bot, kind: str):

    kind = str(kind).strip().lower()
    tasks = await after_tests_db.get_all_pending_by_kind(kind)

    MAX_PER_RUN = 300
    sent = 0
    for row_id, med_id, telegram_id, chat_id in tasks:
        sex = await after_tests_db.get_user_sex(telegram_id)
        anketa = await anamnez_db.get_anketa(telegram_id)
        age = anketa["age"] if anketa["age"] else -100
        if sent >= MAX_PER_RUN:
            break

        if kind == "decode":

            result = await after_tests_db.get_results_only(med_id)
            doc_urls = split_urls_from_cell(result)
            if not result or not str(result).strip():
                continue

            text_to_manager = "Неопознанная ошибка"
            check_result, problems = await check_tests_pdf.check_list_result(links=doc_urls, bot= bot, sex=sex, age= age)
            problems_text = await get_text_problems(problems)
            if check_result == "complete":
                text_to_manager = f"(pending)Пользователь получил расшифровку в автоматическом режиме.Его результаты в пределах нормы.Вот номер его пробирки: {med_id}\nВот ссылки на анализы :\n{doc_urls} \n\n(#Диалог_{telegram_id})."
                await bot.send_message(
                    user_id=telegram_id,
                    text=f"Вот результаты ваших анализов:\n{result}\n\nВаши результаты находятся в пределах нормы."
                )
            elif check_result == "need_consult":
                text_to_manager = f"(pending)Пользователь получил расшифровку в автоматическом режиме.Есть отклонения.Порекомендовал связаться с Татьяной Витальевной в макс. Вот номер его пробирки: {med_id}\nВот ссылки на анализы :\n{doc_urls} \n\n(#Диалог_{telegram_id})."
                await bot.send_message(
                    user_id=telegram_id,
                    text=f"Вот результаты ваших анализов:\n{result}\n\nУ вас есть следующие отклонения от нормы {problems_text}\n\nЯ рекомендую отправить это сообщение нашему специалисту в личный чат MAX для более детального разбора ваших отклонений.\n📩 Связаться со специалистом: +7 918 522-67-09"
                )


            try:
                await after_tests_db.delete_pending_by_id(row_id)
                await send_to_chat(bot= bot, user_id= telegram_id, message_text= text_to_manager )
                sent += 1
                await asyncio.sleep(0.4)

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
        await after_tests_db.sync_tests_job()
        await pending_decode_job(bot)
        await asyncio.sleep(7200)  # каждые 2 часа


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

async def get_text_problems(list_of_lists_dicts: list[list[dict[str, str]]] | None) -> str:
    print(f"LIST   {list_of_lists_dicts}")
    if not list_of_lists_dicts:
        return ""

    text_problems = ""
    unique_items = set()

    for lists in list_of_lists_dicts:
        if not lists:
            continue

        for item in lists:
            if not item:
                continue

            problem_name = item.get("name")
            current_value = item.get("value")
            norm_value = item.get("norm")

            if not problem_name or current_value is None or norm_value is None:
                continue

            key = (problem_name, current_value, norm_value)

            if key in unique_items:
                continue

            unique_items.add(key)

            text_problems += (
                f"{problem_name}:\n"
                f"🧍 Ваш показатель — {current_value}\n"
                f"✅ Норма — {norm_value}\n\n"
            )

    return text_problems.strip()