import random
from utils.anketa_utils import *
from maxapi.context import MemoryContext


def normalize_name(text: str) -> str:
    return ' '.join(word.capitalize() for word in text.strip().split())

async def get_info_by_tests(tests_list, test_info):
    text = ""
    for test in tests_list:
        text += f"{test_info[test]}\n\n"
    return text

async def get_list_and_price(list_tests,tests_price ):
    text = ""
    price = 0
    for test in list_tests:
        text += f"{test} {resources.TESTS_INCLUDE[test]} - {tests_price[test]}₽\n\n"
        price += tests_price[test]

    return text, price

def pick_first_and_two_random(items):
    if len(items) < 3:
        return items
    first = items[0]
    rand_two = random.sample(items[1:], 2)  # берём 2 разных случайных
    return [first] + rand_two

async def validate_anketa_questions(
    position: int,
    user_say: str,
    user_id: int,
    bot
) -> str:
    """
    Возвращает:
        "complete" — если ответ валиден
        "empty" — если выбран невалидный вариант кнопки
        <str>     — текст ошибки
    """

    # ===== ВОПРОСЫ С ФОРМАТНОЙ ВАЛИДАЦИЕЙ =====

    # 0 — ИНН
    if position == 0:
        return validate_inn(user_say)

    # 1 — Дата осмотра
    elif position == 1:
        ok, err = validate_date_input(user_say)
        return "complete" if ok else err

    # 2 — Возраст
    elif position == 2:
        return validate_age(user_say)

    # 3 — Вес
    elif position == 3:
        return validate_weight(user_say)

    # 4 — Рост
    elif position == 4:
        return validate_height(user_say)

    # ===== ВОПРОСЫ С КНОПКАМИ =====

    elif position == 5:
        allowed = ["Да", "Нет", BACK_BUTTON]
        return "complete" if user_say in allowed else "empty"

    elif position == 6:
        allowed = [
            "Не употребляю",
            "По праздникам",
            "Раз в неделю",
            "Раз в месяц",
            BACK_BUTTON
        ]
        return "complete" if user_say in allowed else "empty"

    elif position == 7:
        allowed = ["Высокая", "Средняя", "Низкая", BACK_BUTTON]
        return "complete" if user_say in allowed else "empty"

    elif position == 8:
        allowed = [
            "В норме",
            "Повышенное",
            "Не мониторю",
            "Ниже 120/80",
            BACK_BUTTON
        ]
        return "complete" if user_say in allowed else "empty"

    elif position == 9:
        allowed = ["Да", "Нет", BACK_BUTTON]
        return "complete" if user_say in allowed else "empty"

    elif position == 10:
        allowed = [
            "Сахар всегда в норме",
            "Встречались случаи повышенного",
            "Повышенный",
            "Пониженный",
            "Не мониторю",
            BACK_BUTTON
        ]
        return "complete" if user_say in allowed else "empty"

    elif position == 11:
        allowed = ["Да", "Нет", BACK_BUTTON]
        return "complete" if user_say in allowed else "empty"

    # ===== НЕЙРО-ПРОВЕРКА (12 вопрос) =====

    elif position == 12:
        dialog = await dialogs_db.get_dialog(user_id)

        result = await question_hronic(dialog, bot= bot)

        if "complete" in result:
            # НЕ добавляем в answers здесь!
            # добавление должно происходить в anketa_dialog
            await dialogs_db.delete_dialog(user_id)
            return result

        else:
            await dialogs_db.append_answer(
                telegram_id=user_id,
                text=f"Терапевт сказал:{result}\n"
            )
            return result

    # ===== ПО УМОЛЧАНИЮ =====

    return "complete"

class ContextManager:
    def __init__(self):
        self._contexts = {}

    def get(self, chat_id: int, user_id: int):
        key = (chat_id, user_id)

        if key not in self._contexts:
            self._contexts[key] = MemoryContext(chat_id, user_id)

        return self._contexts[key]

context_manager = ContextManager()
