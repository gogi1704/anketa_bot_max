from datetime import datetime

from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def kb_tests_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "🧪 Сдать Анализы",payload= "tests_main_menu_make_tests"))
    builder.row(CallbackButton(text="🧪 Получить результаты анализов", payload="tests_main_menu_get_tests"))
    builder.row(CallbackButton(text="📊 Расшифровка показателей", payload="tests_main_menu_get_decode"))
    builder.row(CallbackButton(text="🩺 Консультация по результатам анализов", payload="tests_main_menu_consult_med"))
    builder.row(CallbackButton(text="🤖 Поддержка Челика", payload="tests_main_menu_consult_neuro"))

    return builder.as_markup()

def kb_check_up_start():
    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text= "Ознакомиться с комплексами",url=f"https://telegra.ph/CHek-apy-po-laboratorii-OOO-CHelovek-02-06?ver={int(datetime.now().timestamp())}"))
    builder.row(CallbackButton(text="Добавить обследования", payload="сheck_up_start_add"))
    builder.row(CallbackButton(text="Выйти", payload="сheck_up_start_back"))

    return builder.as_markup()

def kb_tests_decode():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Да",payload= "tests_decode_yes"))
    builder.row(CallbackButton(text="Нет", payload="tests_decode_no"))

    return builder.as_markup()

def kb_after_good_tests():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Хочу",payload= "after_good_tests_yes"))
    builder.row(CallbackButton(text="Нет, спасибо", payload="after_good_tests_no"))

    return builder.as_markup()


# def kb_back_complete_check_up():
#     builder = InlineKeyboardBuilder()
#     builder.row(CallbackButton(text= "Вернуться в меню",payload= "choose_type_user_else"))
#
#     return builder.as_markup()
