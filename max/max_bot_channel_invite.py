from maxapi.types import LinkButton, CallbackButton, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder


async def send_channel_invite(event:MessageCallback):
    chat_id,user_id = event.get_ids()

    message_text = (
        "Мы хотим быть полезными не только во время медосмотра, но и каждый день.\n\n"
        "Рекомендуем обратить внимание на наш канал.\n\n"
        "В канале:\n"
        "• советы и рекомендации по здоровью;\n"
        "• разбор анализов и типичных ситуаций;\n"
        "• рекомендации по профилактике и укреплению организма;\n"
        "• полезная информация от наших специалистов.\n\n"
        "Наш канал — ваш надежный помощник в заботе о здоровье (https://t.me/human3s).\n\n"
        "Подписывайтесь, чтобы не пропустить важное ✅"
    )

    builder = InlineKeyboardBuilder()
    builder.row(LinkButton(text= "Открыть канал", url= "https://t.me/human3s"),)
    builder.row(CallbackButton(text= "Написать менеджеру",payload= "reply_to_manager|0"))

    await event.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        attachments=[builder.as_markup()]
    )