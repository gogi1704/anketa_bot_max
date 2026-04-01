from maxapi.types import MessageCreated

import resources
from db.after_tests import after_tests_db as db
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