from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


def kb_choose_osmotr_or_no():
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text= "Буду проходить мед-осмотр",payload= "osmotr_or_yes"))
    builder.row(CallbackButton(text="Нет, не буду", payload="osmotr_or_no"))
    return builder.as_markup()
