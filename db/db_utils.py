from maxapi.types import MessageCreated
from db.after_tests import after_tests_db
from db.anamnez import anamnez_db

async def update_db(event:MessageCreated):
    chat_id, user_id = event.get_ids()
    try:
        await  after_tests_db.sync_to_google_sheets()
        await  anamnez_db.sync_to_google_sheets()
        await event.bot.send_message(user_id=user_id,
                                     text="База данных обновлена")
    except Exception as e:
        await event.bot.send_message(user_id=user_id,
                                     text= f"Ошибка выгрузки базы: {str(e)}")