from maxapi.context import MemoryContext
from maxapi.types import MessageCallback

from ai_agents import open_ai_main
from ai_agents.prompts import BASE_SYSTEM_PROMPT, BASE_USER_PROMPT
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_tests_decode, kb_after_good_tests
from max.max_bot_anamnez.max_bot_navigation import choose_tests

import resources
from max.max_bot_after_tests.max_after_tests_keyboards import tests_keyboards
from db.after_tests import after_tests_db as db
from max.max_bot_chat.max_bot_chat_manager import send_to_chat
from utils.after_tests_utils import write_and_sleep, parse_int, send_wait_emoji, parse_base_answer, \
    replace_wait_with_text
from doc_funs import send_results_doc_and_text, split_urls_from_cell


async def after_tests_main_menu(event):
    chat_id,user_id = event.get_ids()
    user_state = await db.get_user_state(user_id)
    await db.delete_neuro_dialog_states(user_id)
    if user_state is None:
        await db.set_user_state(telegram_id= user_id , user_state= "MAX")


    await event.bot.send_message(
        chat_id=chat_id,
        text=resources.TEXT_TESTS_MAIN_MENU,
        attachments=[tests_keyboards.kb_tests_main_menu()]
    )

async def handle_after_tests_main_menu(event:MessageCallback):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload
    message = event.message

    await write_and_sleep(event, chat_id,2)

    if message:
        await message.delete()


    if data == "tests_main_menu_make_tests":
        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.TEXT_MAKE_CHECK_UP,
            attachments= [tests_keyboards.kb_check_up_start()]
        )

    elif data == "tests_main_menu_get_tests":

        med_id = await db.get_med_id(user_id)

        if med_id:

            doc_url = await db.get_test_results(int(med_id))
            is_tests_bad = await db.get_deviations(int(med_id))

            if doc_url:

                await event.bot.send_message(
                    user_id= user_id,
                    text= resources.TEXT_TESTS_IS_HAS_TRUE
                )

                await write_and_sleep(event = event,
                                      chat_id=chat_id,
                                      sleep_time=5)

                await send_results_doc_and_text(event, doc_url)

                if is_tests_bad:

                    await event.bot.send_message(
                        user_id= user_id,
                        text= resources.TEXT_TESTS_IS_BAD,
                        attachments= [kb_tests_decode()]
                    )

                else:

                    await event.bot.send_message(
                        user_id= user_id,
                        text= resources.TEXT_TESTS_IS_GOOD
                    )

                    await write_and_sleep(event=event,
                                          chat_id=chat_id,
                                          sleep_time=5)

                    await event.bot.send_message(
                        user_id= user_id,
                        text= resources.TEXT_AFTER_GOOD_TESTS,
                        attachments= [kb_after_good_tests()]
                    )

            else:

                await db.add_pending_notification(
                    med_id=int(med_id),
                    telegram_id=user_id,
                    chat_id=chat_id,
                    kind="decode"
                )

                await event.bot.send_message(
                    user_id= user_id,
                    text= resources.TEXT_TESTS_IS_HAS_FALSE
                )

                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=2)

                await after_tests_main_menu(event= event)

        else:

            await db.set_neuro_dialog_states(user_id= user_id,
                                             state= resources.dialog_states["get_med_id"])

            await event.bot.send_message(
                user_id= user_id,
                text= resources.TEXT_TESTS_GET_ID
            )

    elif data == "tests_main_menu_get_decode":

        med_id = await db.get_med_id(user_id)

        if med_id:

            decode = await db.get_test_decode(int(med_id))

            if decode:

                await event.bot.send_message(
                    user_id= user_id,
                    text=f"Вот ваша расшифровка: {decode}"
                )

                await db.set_neuro_dialog_states(
                    user_id,
                    resources.dialog_states["base_speak"]
                )

                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=3)

                await event.bot.send_message(
                    user_id= user_id,
                    text=resources.TEXT_GET_DECODE_COMPLETE_MESSAGE
                )

                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=2)

                await after_tests_main_menu(event= event)
                return

            await event.bot.send_message(
                user_id= user_id,
                text=resources.TEXT_TESTS_IS_HAS_TRUE_DECODE
            )

            await db.add_pending_notification(
                med_id=int(med_id),
                telegram_id=user_id,
                chat_id=chat_id,
                kind="decode"
            )

            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=3)

            await send_manager_get_decode(event, med_id, user_id)

            await db.set_neuro_dialog_states(
                user_id,
                resources.dialog_states["base_speak"]
            )

            await event.bot.send_message(
                user_id= user_id,
                text=resources.TEXT_TESTS_GET_DECODE_FINAL
            )

        else:

            await db.set_neuro_dialog_states(
                user_id,
                resources.dialog_states["get_med_id_decode"]
            )

            await event.bot.send_message(
                user_id= user_id,
                text= resources.TEXT_TESTS_GET_ID
            )

    elif data == "tests_main_menu_consult_med":

        med_id = await db.get_med_id(user_id)

        if med_id:

            number = parse_int(med_id)
            doc_url = await db.get_test_results(number)

            if doc_url:

                await event.bot.send_message(
                    user_id= user_id,
                    text= resources.TEXT_NEW_MED_CONSULT_YES,
                )
                await send_manager_get_consult(event, med_id, doc_url)

                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=3)

                await after_tests_main_menu(event)

            else:

                await event.bot.send_message(
                    user_id= user_id,
                    text= resources.TEXT_NEW_MED_CONSULT_NO,
                )
                await db.add_pending_notification(
                    med_id=int(med_id),
                    telegram_id=user_id,
                    chat_id=chat_id,
                    kind="decode"
                )

                await send_manager_get_consult(event, med_id, doc_url)

                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=3)

                await after_tests_main_menu(event)


        else:

            await db.set_neuro_dialog_states(
                user_id,
                resources.dialog_states["get_med_id_consult"]
            )

            await event.bot.send_message(
                user_id= user_id,
                text=resources.TEXT_TESTS_GET_ID
            )

    elif data == "tests_main_menu_consult_neuro":

        await db.set_neuro_dialog_states(
            user_id,
            resources.dialog_states["base_speak"]
        )

        wait_msg = await send_wait_emoji(event.bot, chat_id)

        dialog = await db.get_dialog(user_id) or "User: Привет"

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=BASE_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )

        answer = parse_base_answer(raw)

        await db.append_answer(user_id, "Assistant", answer)

        await replace_wait_with_text(
            event.bot,
            chat_id,
            wait_msg,
            answer
        )


async def handle_start_check_up(event, context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload
    msg = event.message

    if data == "сheck_up_start_back" :
        await event.bot.send_message(
                chat_id= chat_id,
                text= resources.TEXT_TESTS_MAIN_MENU,
                reply_markup= tests_keyboards.kb_tests_main_menu()
            )
    elif data == "сheck_up_start_add" :
        await choose_tests(event, context_data)
        await msg.delete()

async def handle_decode_yes_no(event:MessageCallback):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload

    med_id = await db.get_med_id(user_id)

    if data == "tests_decode_yes":
        await send_manager_get_decode(event= event,
                                      med_id= med_id,
                                      user_id=user_id)
        await event.bot.send_message(
            user_id= user_id,
            text= resources.TEXT_SEND_TESTS_TO_DECODE)

        await write_and_sleep(event= event,
                              chat_id= chat_id,
                              sleep_time= 3)
        await event.message.delete()

        await event.bot.send_message(
            user_id= user_id,
            text= resources.TEXT_CHELICL_INFO)
        await db.set_neuro_dialog_states(user_id = user_id,
                                         state= resources.dialog_states["base_speak"])

    elif data == "tests_decode_no":
        await write_and_sleep(event=event,
                              chat_id=chat_id,
                              sleep_time=3)
        await event.message.delete()

        await after_tests_main_menu(event=event)

async def send_manager_get_decode(event:MessageCallback, med_id, user_id):
    doc_url = await db.get_test_results(int(med_id))
    doc_urls = split_urls_from_cell(doc_url)
    if doc_url:
        text_to_manager = f"Пользователь просит расшифровать анализы.Вот номер его пробирки: {med_id}\nВот ссылки на анализы :\n{doc_urls} \n\n(#Диалог_{user_id})."
    else:
        text_to_manager = f"Пользователь просит найти его анализы и сделать расшифровку. Вот номер его пробирки: {med_id}\n\n(#Диалог_{user_id})."
    await send_to_chat(event= event,
                       user_id= user_id,
                       message_text= text_to_manager)

async def send_manager_get_consult(event:MessageCallback, med_id, user_id):
    doc_url = await db.get_test_results(int(med_id))
    doc_urls = split_urls_from_cell(doc_url)
    if doc_url:
        text_to_manager = f"Пользователь просит консультацию по результатам анализов.Вот номер его пробирки: {med_id}\nВот ссылки на анализы :\n{doc_urls} \n\n(#Диалог_{user_id})."
    else:
        text_to_manager = f"Пользователь просит консультацию по результатам анализов.Анализы не найдены в таблице.\n Вот номер его пробирки: {med_id}\n\n(#Диалог_{user_id})."
    await send_to_chat(event=event,
                       user_id=user_id,
                       message_text=text_to_manager)

async def handle_after_good_tests_yes_no(event:MessageCallback):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload
    message = event.message

    await write_and_sleep(event=event,
                          chat_id=chat_id,
                          sleep_time=5)
    await message.delete()

    if data == "after_good_tests_yes":
        await db.set_neuro_dialog_states(user_id= user_id,
                                         state= resources.dialog_states["after_tests_get_info"])

        await event.bot.send_message(
            user_id= user_id,
            text= resources.TEXT_QUESTION_AFTER_GOOD_TESTS,
        )

    elif data == "after_good_tests_no":
        await after_tests_main_menu(event=event)