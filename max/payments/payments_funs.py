from maxapi.types import MessageCallback

import resources
from api.api_funs import create_yookassa_payment
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_yookassa, kb_pay_price


async def handle_pay_button_one_consult(event: MessageCallback,amount = 1000):
    chat_id, user_id = event.get_ids()
    payment = await create_yookassa_payment(amount= amount, user_id=user_id, user_email= "test@gmail.com",description= f"Оплата за консультацию({user_id})")
    confirmation_url = payment["confirmation_url"]

    await event.bot.send_message(chat_id = chat_id,
                                 user_id=user_id,
                                 text= "Ссылка для оплаты сформирована.Нажмите на кнопку ниже для оплаты.\n\n\nЕсли ссылка не открывается, проверьте отключен ли у вас VPN (ВПН), и попробуйте нажать на кнопку снова.",
                                 attachments= [kb_yookassa(url= confirmation_url)])



async def handle_pay_price_button(event: MessageCallback):
    chat_id, user_id = event.get_ids()

    await event.bot.send_message(chat_id = chat_id,
                                 user_id=user_id,
                                 text= resources.TEXT_ONE_CONSULT_DESCRIPTION,
                                 attachments= [kb_pay_price()]
                                 )



