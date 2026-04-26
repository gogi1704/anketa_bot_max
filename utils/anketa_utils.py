from maxapi import Bot
import asyncio
import resources
from ai_agents import prompts, open_ai_main
from db.anamnez.anamnez_db import get_all_anketas
from datetime import datetime, timedelta
from maxapi.exceptions.max import MaxApiError

from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_go_to_main_menu
from max.max_bot_chat import max_bot_chat_manager

BACK_BUTTON = "⬅️ Назад"

def validate_date_input(date_text: str):
    date_text = (date_text or "").strip()
    if not date_text:
        return False, "Пустая строка. Введите дату в формате ДД.ММ.ГГГГ (пример: 11.11.2025)."

    # Приводим все разделители к точке
    normalized = date_text.replace("-", ".").replace("/", ".")

    try:
        user_date = datetime.strptime(normalized, "%d.%m.%Y").date()
    except ValueError:
        return False, "Введите дату в формате ДД.ММ.ГГГГ (пример: 12.12.2025)."

    today = datetime.today().date()
    if user_date < today:
        return False, "Возможно, вы случайно ввели прошедшую дату. Введите корректное значение, в формате ДД.ММ.ГГГГ (пример: 12.12.2025). "

    return True, None

def is_valid_inn(inn: str) -> bool:
    if not inn.isdigit():
        return False

    length = len(inn)

    def check_digit(digits, coefficients):
        s = sum(int(d) * c for d, c in zip(digits, coefficients))
        return str((s % 11) % 10)

    if length == 10:
        coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        return inn[-1] == check_digit(inn[:9], coefficients)
    elif length == 12:
        coefficients1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
        coefficients2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8, 0]
        return (inn[-2] == check_digit(inn[:11], coefficients1) and
                inn[-1] == check_digit(inn[:11], coefficients2))
    return False

def validate_inn(inn_text):
    if not inn_text.isdigit() or len(inn_text) not in (10, 12):
        return "❌ ИНН должен состоять только из 10 или 12 цифр. Попробуйте ещё раз."


    if not is_valid_inn(inn_text):
        return "❌ Неверный ИНН. Проверьте и введите снова."


    return "complete"

def validate_age(value: str) -> str:
    if not value.isdigit():
        return "Пожалуйста, введите только цифру равную вашему возрасту (пример ввода : 33)"
    age = int(value)
    if age < 18:
        return "Возраст не может быть меньше 18 лет. Пожалуйста, введите корректное значение."
    if age > 100:
        return "Скорее всего, вы допустили ошибку при введении данных возраста.Но, если вам реально больше 100 лет, то мы безумно рады за вас и желаем вам крепкого здоровья. Если вам больше 100 лет, то введите просто цифру 100. "

    return "complete"  # Всё хорошо

def validate_weight(value: str) -> str:
    if not value.isdigit():
        return "Пожалуйста, введите только цифру равную вашему весу (пример ввода : 84)"
    weight = int(value)
    if weight < 20:
        return "Указан слишком маленький вес. Возможно вы ошиблись при вводе данных. Пожалуйста, введите корректное значение."
    if weight > 250:
        return "Указан слишком большой вес. Возможно вы ошиблись при вводе данных. Пожалуйста, введите корректное значение."

    return "complete"  # Всё хорошо

def validate_height(value: str) -> str:
    if not value.isdigit():
        return "Пожалуйста, введите только цифру равную вашему росту в сантиметрах (пример ввода : 184)"
    height = int(value)
    if height < 140:
        return "Указан слишком маленький рост. Возможно вы ошиблись при вводе данных. Пожалуйста, введите корректное значение."
    if height > 250:
        return "Указан слишком большой рост. Возможно вы ошиблись при вводе данных. Пожалуйста, введите корректное значение."

    return "complete"  # Всё хорошо

def question_smoke():
    keyboard = [
        ["Да", "Нет"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    return resources.QUESTIONS[5], keyboard

def question_alko():
    keyboard = [
        ["Не употребляю","По праздникам"],
        ["Раз в неделю", "Раз в месяц"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    return resources.QUESTIONS[6], keyboard

def question_physical():
    keyboard = [
        ["Высокая","Средняя"],
        ["Низкая"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    return resources.QUESTIONS[7], keyboard

def question_hyperton():
    keyboard = [
        ["В норме", "Не мониторю"],
        ["Повышенное", "Ниже 120/80"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    return resources.QUESTIONS[8], keyboard

def question_dark_in_eyes():
    keyboard = [
        ["Да","Нет"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    return resources.QUESTIONS[9], keyboard

def question_sugar():
    keyboard = [
        ["Сахар всегда в норме"],
        ["Повышенный","Пониженный"],
        ["Не мониторю"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    return resources.QUESTIONS[10], keyboard

def question_sustavi():
    keyboard = [
        ["Да","Нет"],
        [BACK_BUTTON]
    ]
    # reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    return resources.QUESTIONS[11], keyboard

# async def question_hyperton(dialog, context):
#     user_prompt = prompts.user_prompt_check_hyperton_question.format(dialog=dialog)
#     agent_check = await open_ai_main.get_gpt_answer(system_prompt= prompts.system_prompt_check_hyperton_question, user_prompt=user_prompt, context= context)
#     return agent_check

async def question_hronic(dialog, bot):
    user_prompt = prompts.user_prompt_check_hronic_question.format(dialog=dialog)
    agent_check = await open_ai_main.get_gpt_answer(system_prompt= prompts.system_prompt_check_hronic_question, user_prompt=user_prompt, bot= bot)
    return agent_check

async def get_users_with_osmotr_tomorrow() -> list[dict]:
    anketas = await get_all_anketas()

    tomorrow = (datetime.now(resources.MOSCOW_TZ) + timedelta(days=1)).date()
    result = []

    for anketa in anketas:
        osmotr_date_raw = anketa.get("osmotr_date")

        if not osmotr_date_raw:
            continue

        try:
            osmotr_date = datetime.strptime(
                str(osmotr_date_raw).strip(),
                "%d.%m.%Y"
            ).date()
        except ValueError:
            print(f"Некорректный формат даты у user_id={anketa.get('user_id')}: {osmotr_date_raw}")
            continue

        if osmotr_date == tomorrow:
            result.append(anketa)
    return result

async def send_osmotr_tomorrow_notifications(bot:Bot):
    users = await get_users_with_osmotr_tomorrow()

    if not users:
        print("Нет пользователей с осмотром завтра")
        return
    users_count = len(users)
    for user in users:
        user_id = user["user_id"]

        try:
            await bot.send_message(
                user_id=user_id,
                text=resources.TEXT_REMINDER,
                attachments= [kb_go_to_main_menu()]

            )

        except MaxApiError as e:
            users_count -= 1
            raw = getattr(e, "raw", {}) or {}

            if getattr(e, "code", None) == 403 and raw.get("code") == "chat.denied":
                print(f"Нельзя отправить сообщение user_id={user_id}: {raw}")
                continue

            print(f"Ошибка отправки user_id={user_id}: {e}")
            continue

        except Exception as e:
            users_count -= 1
            print(f"Неизвестная ошибка отправки user_id={user_id}: {e}")
            continue

    await max_bot_chat_manager.send_to_chat(bot, user_id = 206156549, message_text= f"Напоминания отправлены пользователям.\nВсего найдено пользователей: {len(users)}\nУспешно отправлено: {users_count}")

async def osmotr_notification_scheduler(bot):
    while True:
        now = datetime.now(resources.MOSCOW_TZ)

        next_run = now.replace(hour=7, minute=0, second=0, microsecond=0)

        if now >= next_run:
            next_run += timedelta(days=1)

        sleep_seconds = (next_run - now).total_seconds()

        print(f"Следующая проверка уведомлений: {next_run}")
        await asyncio.sleep(sleep_seconds)

        try:
            await send_osmotr_tomorrow_notifications(bot)
        except Exception as e:
            print(f"Ошибка в osmotr_notification_scheduler: {e}")
