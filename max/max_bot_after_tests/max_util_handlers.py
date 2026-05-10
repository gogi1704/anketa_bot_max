from maxapi.types import MessageCreated

import resources
from api.api_funs import create_yookassa_payment
from db.after_tests import after_tests_db as db
from db.anamnez import anamnez_db as anamnez_db
from max.max_bot_after_tests.max_after_tests_keyboards import tests_keyboards
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_yookassa


async def get_statistic_by_inn(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
        user_id,
        resources.dialog_states["stat_inn"]
    )

    await event.bot.send_message(
        chat_id=chat_id,
        text= "Введите инн :\n\n\n Или нажмите кнопку для отмены",
        attachments=[tests_keyboards.kb_statistic_inn_close()]
    )

async def get_statistic_inn_by_date(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
            user_id,
            resources.dialog_states["get_stat_inn_by_date"]
    )

    await event.bot.send_message(
            chat_id=chat_id,
            text="Введите полную дату :\n\n\n Или нажмите кнопку для отмены",
            attachments=[tests_keyboards.kb_statistic_inn_close()]
        )

async def get_dop_tests_statistic(event: MessageCreated):
    chat_id, _ = event.get_ids()
    result = await anamnez_db.get_dop_tests_stats()
    print(result)
    await event.bot.send_message(
            chat_id=chat_id,
            text= result
        )

async def handle_send_post_with_bt (event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
        user_id,
        resources.dialog_states["send_post_with_bt"]
    )

    await event.bot.send_message(
        chat_id=chat_id,
        text= "Пришлите пост и он будет отправлен с кнопками! (Наш канал и Главное меню)",
    )

async def handle_send_post_without_bt(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
        user_id,
        resources.dialog_states["send_post_without_bt"]
    )

    await event.bot.send_message(
        chat_id=chat_id,
        text= "Пришлите пост и он будет с одной кнопкой! (Главное меню)",
    )

async def get_price(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    await event.bot.send_message(
        chat_id=chat_id,
        text=resources.text_fake_price,
        attachments= [tests_keyboards.kb_price()]
    )

async def make_pay_50(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    payment = await create_yookassa_payment(amount= 50, user_id=user_id, user_email= "test@gmail.com",description= f"Оплата за консультацию({user_id})")
    confirmation_url = payment["confirmation_url"]

    await event.bot.send_message(chat_id = chat_id,
                                 user_id=user_id,
                                 text= "Ссылка для оплаты сформирована.Нажмите на кнопку ниже для оплаты.\n\n\nЕсли ссылка не открывается, проверьте отключен ли у вас VPN (ВПН), и попробуйте нажать на кнопку снова.",
                                 attachments= [kb_yookassa(url= confirmation_url)])
