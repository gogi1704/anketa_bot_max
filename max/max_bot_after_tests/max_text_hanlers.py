import asyncio
from maxapi.types import MessageCreated

from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_go_to_main_menu
from max.max_bot_after_tests.max_bot_after_tests_main_menu import handle_get_med_id, handle_get_med_id_decode, \
    handle_get_med_id_consult, handle_base_speak, handle_manager_collect, handle_boss_collect
from max.max_bot_chat import max_bot_cha_manager_after_tests
from db.after_tests import after_tests_db as db
from db.anamnez import anamnez_db
from resources import dialog_states



async def handle_text_message_after_tests(event:MessageCreated):

    message = event.message
    bot = event.bot
    chat_id, user_id = event.get_ids()
    text = message.body.text.strip()

    state = await db.get_neuro_dialog_states(user_id)
    dialog = await db.get_dialog(user_id) or ""

    manager_msg_id = await db.get_user_answer_state(user_id)
    if manager_msg_id is not None:

        await db.delete_user_answer_state(user_id)

        await max_bot_cha_manager_after_tests.send_to_chat(
            event = event,
            user_id= user_id,
            message_text= f"📨 Пользователь ответил:\n\n{text}\n\n#Диалог_{user_id}"
        )

        await bot.send_message(
            user_id=user_id,
            text="✅ Ваш ответ отправлен менеджеру."
        )
        return

    user_data = await anamnez_db.get_user(user_id)
    anketa = await  anamnez_db.get_anketa(user_id)
    sex = await db.get_user_sex(user_id)

    name = user_data["name"] if user_data["name"] else "Не заполнено"
    age = anketa["age"] if anketa["age"] else -100

    if state == dialog_states["stat_inn"]:
        report = await anamnez_db.get_report_by_inn(text)
        await event.bot.send_message(chat_id= chat_id,
                                     text = report)
        return

    if state == dialog_states["get_stat_inn_by_date"]:
        report = await anamnez_db.get_unique_organizations_report_since_date(text)
        await event.bot.send_message(chat_id= chat_id,
                                     text = report)
        return


    if state == dialog_states["after_tests_get_info"]:

        text_to_manager = (
            f"У Пользователя (Имя: {name}\nВозраст: {age})\n все в порядке с анализами, "
            f"но он хочет поговорить со специалистом.\n"
            f"Описание: {text}\n\n(#Диалог_{user_id})"
        )

        await max_bot_cha_manager_after_tests.send_to_chat(event = event,
                                                user_id= user_id,
                                                message_text= text_to_manager)

        await complete_dialog(user_id, "Дайте знать, если вам что то понадобится!")

        await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])

        await asyncio.sleep(2)

        await bot.send_message(
            chat_id=chat_id,
            text="Дайте знать, если вам что то понадобится",
            attachments= [kb_go_to_main_menu()]
        )
        return

    elif state == dialog_states["get_med_id"]:
        await handle_get_med_id(event)

    elif state == dialog_states["get_med_id_decode"]:
        await handle_get_med_id_decode(event, sex, age)

    elif state == dialog_states["get_med_id_consult"]:
        await handle_get_med_id_consult(event, sex, age)

    elif state == dialog_states["base_speak"]:
        await handle_base_speak(event, dialog, name, age)

    elif state in (dialog_states["med_collect"], dialog_states["manager_collect"]):
        await handle_manager_collect(event, dialog, state, name, age)

    elif state == dialog_states["boss_collect"]:
        await handle_boss_collect(event, dialog, name, age)

    else:

        # ===============================
        # FALLBACK
        # ===============================
        await event.bot.send_message(
            user_id= user_id,
            text="Для начала завершите текущий сценарий с кнопками или отправьте боту команду: /start."
        )

async def complete_dialog(user_id: int, last_text: str):
    await db.delete_dialog(user_id)
    await db.append_answer(user_id, "Assistant", last_text)