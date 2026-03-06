import asyncio
from maxapi.types import MessageCreated
from ai_agents import open_ai_main
from max.max_bot_chat import max_bot_chat_manager
from db.after_tests import after_tests_db as db
from resources import dialog_states
from ai_agents.prompts import BASE_SYSTEM_PROMPT, BASE_USER_PROMPT, COLLECT_SYSTEM_PROMPT
from utils import  after_tests_utils


async def handle_text_message_after_tests(event:MessageCreated):

    message = event.message
    bot = event.bot

    # if not message.body or not getattr(message.body, "text", None):
    #     return

    chat_id, user_id = event.get_ids()
    text = message.body.text.strip()

    state = await db.get_neuro_dialog_states(user_id)
    dialog = await db.get_dialog(user_id) or ""

    def add(role, msg):
        return dialog + f"\n{role}: {msg}"

    manager_msg_id = await db.get_user_answer_state(user_id)

    # ===============================
    # ОТВЕТ МЕНЕДЖЕРУ
    # ===============================
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

    # ===============================
    # AFTER TESTS
    # ===============================
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

    # ===============================
    # BASE SPEAK
    # ===============================
    if state == dialog_states["base_speak"]:

        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)

        # отправляем ⏳
        wait_msg = await bot.send_message(chat_id=chat_id, text="⏳")

        raw = await open_ai_main.get_gpt_answer(
            BASE_SYSTEM_PROMPT,
            BASE_USER_PROMPT.format(dialog=dialog)
        )

        answer = after_tests_utils.parse_base_answer(raw)

        # ---------- ПЕРЕДАТЬ СПЕЦИАЛИСТУ ----------
        if answer == "get_med":

            await db.set_neuro_dialog_states(user_id, dialog_states["manager_collect"])

            raw = await open_ai_main.get_gpt_answer(
                system_prompt=COLLECT_SYSTEM_PROMPT,
                user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
            )

            decision = after_tests_utils.parse_base_answer(raw)

            await db.append_answer(user_id, "Assistant", decision)

            await bot.edit_message(
                message_id= wait_msg.message.body.mid,
                text= decision
            )
            return

        # ---------- ОБЫЧНЫЙ ОТВЕТ ----------
        dialog = add("Assistant", answer)
        await db.append_answer(user_id, "Assistant", answer)

        await bot.edit_message(
            message_id= wait_msg.message.body.mid,
            text= answer
        )
        return

    # ===============================
    # COLLECT (MANAGER / MED)
    # ===============================
    if state in (dialog_states["med_collect"], dialog_states["manager_collect"]):

        dialog = add("User", text)
        await db.append_answer(user_id, "User", text)

        wait_msg = await bot.send_message(chat_id=chat_id, text="⏳")

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )

        result, data = after_tests_utils.pars_answer_and_data(raw)

        if result == "complete":

            text_to_manager = (
                f"Пользователь просит помощи.\n"
                f"Описание: {data}\n\n(#Диалог_{user_id})"
            )

            await max_bot_chat_manager.send_to_chat(event= event.bot,
                                                    user_id= user_id,
                                                    message_text= text_to_manager)

            await db.set_neuro_dialog_states(user_id, dialog_states["base_speak"])

            await bot.edit_message(
                message_id=wait_msg.message.body.mid,
                text="Спасибо. Информация передана специалисту."
            )
            return

        await db.append_answer(user_id, "Assistant", result)

        await bot.edit_message(
            message_id=wait_msg.message.body.mid,
            text=result
        )
        return

    # ===============================
    # FALLBACK
    # ===============================
    await bot.send_message(
        chat_id=chat_id,
        text="Для начала завершите текущий сценарий с кнопками или используйте /start."
    )

async def complete_dialog(user_id: int, last_text: str):
    await db.delete_dialog(user_id)
    await db.append_answer(user_id, "Assistant", last_text)