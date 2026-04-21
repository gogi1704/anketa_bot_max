import asyncio
from maxapi.types import MessageCreated

from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_go_to_main_menu, \
    kb_send_post_without_bt, kb_send_post_with_bt
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
    age = 0
    name = "Не заполнено"
    if user_data:
        name = user_data["name"] if user_data["name"] else "Не заполнено"

    if anketa:
        age = anketa["age"] if anketa["age"] else 0

    if state == dialog_states["send_post_with_bt"]:
        user_ids = await anamnez_db.get_all_user_ids()
        post_text = event.message.body.text
        attach = event.message.body.attachments
        if attach:
            attach.append(kb_send_post_with_bt())
        else:
            attach = [kb_send_post_with_bt()]

        if event.message.body is None:
            await event.message.answer("Невозможно выполнить рассылку: у сообщения отсутствует body")
            return
        success_count = 0
        error_count = 0

        for user_id in user_ids:
            try:
                await event.bot.send_message(
                    user_id=user_id,
                    attachments=attach,
                    text= post_text
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Ошибка отправки пользователю {user_id}: {e}")

            await asyncio.sleep(0.05)
        await db.delete_neuro_dialog_states(user_id)
        await event.message.answer(
            f"Рассылка завершена.\n"
            f"Успешно: {success_count}\n"
            f"Ошибок: {error_count}"
        )
        return

    if state == dialog_states["send_post_without_bt"]:
        user_ids = await anamnez_db.get_all_user_ids()
        attach = event.message.body.attachments
        post_text = event.message.body.text
        if attach:
            attach.append(kb_send_post_without_bt())
        else:
            attach = [kb_send_post_without_bt()]
        if event.message.body is None:
            await event.message.answer("Невозможно выполнить рассылку: у сообщения отсутствует body")
            return
        success_count = 0
        error_count = 0

        for user_id in user_ids:
            try:
                await event.bot.send_message(
                    user_id=user_id,
                    attachments=attach,
                    text= post_text
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Ошибка отправки пользователю {user_id}: {e}")

            await asyncio.sleep(0.05)
        await db.delete_neuro_dialog_states(user_id)
        await event.message.answer(
            f"Рассылка завершена.\n"
            f"Успешно: {success_count}\n"
            f"Ошибок: {error_count}",
        )
        return

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