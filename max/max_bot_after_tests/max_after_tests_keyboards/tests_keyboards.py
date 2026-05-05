from datetime import datetime

from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def kb_tests_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="🪢 Привязать пробирку", payload="tests_main_menu_connect_result_number"))
    builder.row(CallbackButton(text= "🧪 Сдать Анализы",payload= "tests_main_menu_make_tests"))
    builder.row(CallbackButton(text="🧪 Получить результаты анализов", payload="tests_main_menu_get_tests"))
    builder.row(CallbackButton(text="📊 Расшифровка показателей", payload="tests_main_menu_get_decode"))
    builder.row(CallbackButton(text="🩺 Консультация по результатам анализов", payload="tests_main_menu_consult_med"))
    builder.row(CallbackButton(text="🤖 Поддержка Челика", payload="tests_main_menu_consult_neuro"))
    builder.row(CallbackButton(text="Ваш врач", payload="doctor_info"))
    builder.row(LinkButton(text="Самый полезный канал в Max",
                           url=f"https://max.ru/join/e1EbeWGW5wqMzQem_0ADl_1-S3MsUKwj-Dx5AbkZ0Do"))

    return builder.as_markup()

def kb_check_up_start():
    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text= "Ознакомиться с комплексами",url=f"https://docs.google.com/document/d/1oEsDgDVVocJ9pQWVc6iH08T5kFT85qWv1y-in_BV0PY/edit?usp=sharing"))
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


def kb_tests_decode_empty():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Попросить лаборанта",payload= "empty_decode_get_laborant"))
    builder.row(CallbackButton(text="Обратиться к менеджеру", payload="empty_decode_get_manager"))

    return builder.as_markup()

def kb_go_to_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Главное меню",payload= "go_to_main_menu"))

    return builder.as_markup()

def kb_statistic_inn_close():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Отмена",payload= "go_to_main_menu"))

    return builder.as_markup()

def kb_get_your_sex():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Мужчина",payload= "get_your_sex_man"))
    builder.row(CallbackButton(text="Женщина", payload="get_your_sex_woman"))

    return builder.as_markup()

def kb_send_post_without_bt():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="Главное меню", payload="go_to_main_menu"))

    return builder.as_markup()

def kb_send_post_with_bt():
    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text= "Открыть сообщество", url="https://max.ru/join/e1EbeWGW5wqMzQem_0ADl_1-S3MsUKwj-Dx5AbkZ0Do" ))
    builder.row(CallbackButton(text="Главное меню", payload="go_to_main_menu"))

    return builder.as_markup()

def kb_to_doc_chat():
    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text="💬 Связь с специалистом",  url= "https://max.ru/u/f9LHodD0cOIWhj3BuueIOPTrf4xQibmR61Y3vcgmZ18rqaDnoC6nZt6YBNs"))
    builder.row(CallbackButton(text="Подробнее о враче", payload="doctor_info"))

    return builder.as_markup()

def kb_price():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Единоразовая консультация",payload= "price_once"))
    builder.row(CallbackButton(text="Месячная подписка", payload="price_month"))
    builder.row(CallbackButton(text="Главное меню", payload="go_to_main_menu"))

    return builder.as_markup()
