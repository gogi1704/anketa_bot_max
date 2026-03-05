from maxapi.types import CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def kb_tests_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "🧪 Сдать Анализы",payload= "tests_main_menu_make_tests"))
    builder.row(CallbackButton(text="🧪 Получить результаты анализов", payload="tests_main_menu_get_tests"))
    builder.row(CallbackButton(text="📊 Расшифровка показателей", payload="tests_main_menu_get_decode"))
    builder.row(CallbackButton(text="🩺 Консультация по результатам анализов", payload="tests_main_menu_consult_med"))
    builder.row(CallbackButton(text="🤖 Поддержка Челика", payload="tests_main_menu_consult_neuro"))

    return builder.as_markup()