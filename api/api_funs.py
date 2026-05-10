import httpx
from maxapi import Bot

import resources
from db.after_tests.after_tests_db import save_message_link
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_go_to_main_menu


async def create_yookassa_payment(amount: int,
    user_id: int,
    user_email: str,
    description: str):

    async with httpx.AsyncClient(verify= False) as client:

        response = await client.post(
            "https://cheloveckmed.ru/payments/create-payment",
            json={
                "user_id": user_id,
                "user_email": user_email,
                "description": description,
                "amount": amount
            }
        )

        data = response.json()

        return data


async def pay_completed(user_id: int, bot:Bot):
    await bot.send_message(user_id= user_id,
                           text= f"{resources.TEXT_PAY_COMPLETE}\n\n\n#id_{user_id}",
                           attachments=[kb_go_to_main_menu()]
                           )
    await send_to_chat(user_id= user_id, message_text= f"Оплата прошла успешно!.\n\n\n#Диалог_{user_id}", bot= bot)



async def pay_canceled(user_id: int, bot:Bot):
    await bot.send_message(user_id= user_id,
                           text= resources.TEXT_PAY_CANCELED,
                           attachments=[kb_go_to_main_menu()]
                           )
    await send_to_chat(user_id= user_id, message_text= f"Оплата была отменена или вышел срок действия ссылки.\n\n\n#Диалог_{user_id}", bot= bot)


async def send_to_chat(bot:Bot, user_id: int, message_text: str):
    sent = await bot.send_message(
        chat_id=resources.GROUP_CHAT_ID,
        text=message_text
    )

    await save_message_link(
        group_msg_id= sent.message.body.seq,
        user_id=user_id
    )

