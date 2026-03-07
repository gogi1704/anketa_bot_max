from maxapi.types import MessageCreated, MessageCallback, CallbackButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

import resources
from db.after_tests.after_tests_db import save_message_link, save_user_answer_state, get_user_id_by_group_message


async def send_to_chat(event, user_id: int, message_text: str):
    sent = await event.bot.send_message(
        chat_id=resources.GROUP_CHAT_ID,
        text=message_text
    )

    await save_message_link(
        group_msg_id= sent.message.body.seq,
        user_id=user_id
    )

async def handle_reply_button_pressed(event:MessageCallback):
    chat_id, user_id = event.get_ids()
    payload = event.callback.payload

    _, manager_msg_id = payload.split("|")
    manager_msg_id = int(manager_msg_id)


    # Удаляем кнопку (если SDK поддерживает)
    try:
        await event.bot.edit_message(
            message_id=event.message.body.mid,
            attachments=None
        )
    except Exception as e:
        print(f"⚠ Не удалось удалить кнопку: {e}")

    # Если пользователь нажал "Написать менеджеру"
    if manager_msg_id == 0:
        await save_user_answer_state(user_id, 0)

        await event.bot.send_message(
            chat_id=chat_id,
            text="✍️ Напишите ваш вопрос менеджеру одним сообщением."
        )
        return

    # Если это ответ на конкретное сообщение менеджера
    await save_user_answer_state(user_id, manager_msg_id)

    await event.bot.send_message(
        chat_id=chat_id,
        text="✍️ Введите ваш ответ менеджеру:"
    )

async def handle_manager_reply(event:MessageCreated):
    linked_message = event.message.link
    if linked_message:
        group_message_id = linked_message.message.seq

        user_id = await get_user_id_by_group_message(group_message_id)

        if user_id:
            builder = InlineKeyboardBuilder()
            builder.row(
                CallbackButton(text="✉ Нажмите чтобы ответить",
                               payload=f"reply_to_manager|{event.message.body.seq}")
            )

            await event.bot.send_message(
                user_id=user_id,
                text=(
                    "📩 Сообщение от менеджера:\n\n"
                    f"{event.message.body.text}\n\n"
                    "Для ответа нажмите кнопку ниже и отправьте текст одним сообщением."
                ),
                attachments= [builder.as_markup()]
            )

            await event.message.reply("✅ Ответ отправлен пользователю.")
        else:
            await event.message.reply("⚠️ Не удалось найти пользователя по сообщению.")

    else:
        await event.message.reply("⚠️ Это не ответ на сообщение пользователя.")
        return