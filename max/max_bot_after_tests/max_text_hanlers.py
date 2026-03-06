import asyncio
from token import AWAIT

from maxapi.types import MessageCreated
from ai_agents import open_ai_main
from max.max_bot_after_tests.max_bot_after_tests_main_menu import handle_get_med_id, handle_get_med_id_decode, \
    handle_get_med_id_consult, handle_base_speak, handle_manager_collect
from max.max_bot_chat import max_bot_chat_manager
from db.after_tests import after_tests_db as db
from max.max_bot_chat.max_bot_chat_manager import send_to_chat
from resources import dialog_states
from ai_agents.prompts import BASE_SYSTEM_PROMPT, BASE_USER_PROMPT, COLLECT_SYSTEM_PROMPT, BOSS_COLLECT_SYSTEM_PROMPT
from utils import  after_tests_utils
from utils.after_tests_utils import send_wait_emoji, pars_answer_and_data, replace_wait_with_text


async def handle_text_message_after_tests(event:MessageCreated):

    message = event.message
    bot = event.bot
    chat_id, user_id = event.get_ids()
    text = message.body.text.strip()

    state = await db.get_neuro_dialog_states(user_id)
    dialog = await db.get_dialog(user_id) or ""

    def add(role, msg):
        return dialog + f"\n{role}: {msg}"

    manager_msg_id = await db.get_user_answer_state(user_id)
    if manager_msg_id is not None:

        await db.delete_user_answer_state(user_id)

        await max_bot_chat_manager.send_to_chat(
            event = event,
            user_id= user_id,
            message_text= f"📨 Пользователь ответил:\n\n{text}\n\n#Диалог_с_{user_id}"
        )

        await bot.send_message(
            chat_id=user_id,
            text="✅ Ваш ответ отправлен менеджеру."
        )
        return



    if state == dialog_states["after_tests_get_info"]:

        text_to_manager = (
            f"У пользователя все в порядке с анализами, "
            f"но он хочет поговорить со специалистом.\n"
            f"Описание: {text}\n\n(#Диалог_{user_id})"
        )

        await max_bot_chat_manager.send_to_chat(event = event,
                                                user_id= user_id,
                                                message_text= text_to_manager)

        await complete_dialog(user_id, "Дайте знать, если вам что то понадобится!")

        await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])

        await asyncio.sleep(2)

        await bot.send_message(
            chat_id=chat_id,
            text="Дайте знать, если вам что то понадобится"
        )
        return

    elif state == dialog_states["get_med_id"]:
        await handle_get_med_id(event)

    elif state == dialog_states["get_med_id_decode"]:
        await handle_get_med_id_decode(event)

    elif state == dialog_states["get_med_id_consult"]:
        await handle_get_med_id_consult(event)

    elif state == dialog_states["base_speak"]:
        await handle_base_speak(event, dialog)

    elif state in (dialog_states["med_collect"], dialog_states["manager_collect"]):
        await handle_manager_collect(event, dialog, state)


    elif state == dialog_states["boss_collect"]:
        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)

        # >>> ДОБАВЛЕНО
        wait_msg = await send_wait_emoji(event.bot,chat_id)
        # <<< ДОБАВЛЕНО

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=BOSS_COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )

        result, data = pars_answer_and_data(raw)

        if result == "complete":
            print("boss_complete")
            await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
            # Отправка в группу
            text_to_manager = f"Пользователь обращается к руководству. У него следующая проблема :{data} \n\n(#Диалог_{user_id}). "
            await send_to_chat(event.bot, chat_id, text_to_manager)

            await replace_wait_with_text(event.bot, chat_id, wait_msg, "Спасибо. Ваше обращение передано руководству.")
            await complete_dialog(user_id= user_id,
                                  last_text="Дайте знать, если вам что то понадобится!")
            return

        elif result == "back":
            msg_text = "Ок. Дайте знать, если вам что то понадобится"
            await complete_dialog(user_id= user_id,
                                  last_text=msg_text)

            await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])
            await replace_wait_with_text(event.bot, chat_id, wait_msg, msg_text)
            return

        dialog = add("Assistant", result)
        await db.append_answer(user_id, "Assistant", result)
        await replace_wait_with_text(event.bot, chat_id, wait_msg, result)
        return

    else:

        # ===============================
        # FALLBACK
        # ===============================
        await event.bot.send_message(
            user_id= user_id,
            text="Для начала завершите текущий сценарий с кнопками или используйте /start."
        )

async def complete_dialog(user_id: int, last_text: str):
    await db.delete_dialog(user_id)
    await db.append_answer(user_id, "Assistant", last_text)