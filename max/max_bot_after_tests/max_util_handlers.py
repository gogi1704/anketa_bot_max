from maxapi.types import MessageCreated

import resources
from db.after_tests import after_tests_db as db
from db.anamnez import anamnez_db as anamnez_db
from max.max_bot_after_tests.max_after_tests_keyboards import tests_keyboards


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