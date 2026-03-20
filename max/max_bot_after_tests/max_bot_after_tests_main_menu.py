import asyncio

from maxapi.context import MemoryContext
from maxapi.enums.sender_action import SenderAction
from maxapi.types import MessageCallback, MessageCreated

from ai_agents import open_ai_main
from ai_agents.prompts import BASE_SYSTEM_PROMPT, BASE_USER_PROMPT, COLLECT_SYSTEM_PROMPT, BOSS_COLLECT_SYSTEM_PROMPT
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_tests_decode, kb_after_good_tests, \
    kb_tests_decode_empty, kb_check_up_start, kb_tests_main_menu, kb_go_to_main_menu
from max.max_bot_anamnez.max_bot_navigation import choose_tests

import resources
from max.max_bot_after_tests.max_after_tests_keyboards import tests_keyboards
from db.after_tests import after_tests_db as db
from max.max_bot_chat.max_bot_cha_manager_after_tests import send_to_chat
from utils.after_tests_utils import write_and_sleep, parse_int, send_wait_emoji, parse_base_answer, \
    replace_wait_with_text, pars_answer_and_data
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

async def handle_after_tests_main_menu(event:MessageCallback, name, age):
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

            await send_manager_get_decode(event, med_id, user_id, name, age)

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
                await send_manager_get_consult(event, med_id, user_id, name, age)

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

                await send_manager_get_consult(event, med_id, user_id, name, age)

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

        await db.delete_dialog(user_id)

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


async def handle_get_med_id(event:MessageCreated):
    chat_id, user_id = event.get_ids()
    med_id = event.message.body.text
    number = parse_int(med_id)
    print(f"handle_get_med_id\nтекст{med_id}\nномер{number}")

    if number is None:
        await event.message.answer(
            "❌ Нужно ввести целое число.\nПопробуйте ещё раз:"
        )
        return
    else:
        await db.create_dialog_user_with_med_id(user_id, med_id)
        await db.delete_neuro_dialog_states(user_id)

        doc_url = await db.get_test_results(number)
        is_tests_bad = await db.get_deviations(number)

        if doc_url:
            await event.message.answer(text=resources.TEXT_TESTS_IS_HAS_TRUE)
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=4)
            await send_results_doc_and_text(event= event,
                                            doc_urls=  doc_url)

            if is_tests_bad:
                await event.bot.send_message(
                    user_id= user_id,
                    text=resources.TEXT_TESTS_IS_BAD,
                    attachments= [tests_keyboards.kb_tests_decode()]
                )
            else:
                await event.message.answer(text=resources.TEXT_TESTS_IS_GOOD)
                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=2)

                await event.bot.send_message(
                    user_id= user_id,
                    text=resources.TEXT_AFTER_GOOD_TESTS,
                    attachments= [kb_after_good_tests()]
                )
        else:
            await db.add_pending_notification(
                med_id= number,
                telegram_id= user_id,
                chat_id= chat_id,
                kind="decode"
            )

            await event.message.answer(text=resources.TEXT_TESTS_IS_HAS_FALSE)
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=2)

            await event.bot.send_message(
                user_id= user_id,
                text= resources.TEXT_TESTS_MAIN_MENU,
                attachments= [tests_keyboards.kb_tests_main_menu()]
            )

async def handle_get_med_id_decode(event:MessageCreated, name, age):
    chat_id, user_id = event.get_ids()
    med_id = event.message.body.text
    number = parse_int(med_id)
    print(f"handle_get_med_id\nтекст{med_id}\nномер{number}")

    if number is None:
        await event.message.answer(
            "❌ Нужно ввести целое число.\nПопробуйте ещё раз:"
        )
        return
    else:
        await db.create_dialog_user_with_med_id(user_id , med_id)
        await db.delete_neuro_dialog_states(user_id)
        doc_url = await db.get_test_results(number)

        if doc_url:
            await db.add_pending_notification(
                med_id=int(med_id),
                telegram_id= user_id,
                chat_id= chat_id,
                kind="decode"
            )

            await event.message.answer(text=resources.TEXT_TESTS_IS_HAS_TRUE_DECODE)
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=3)

            await send_manager_get_decode(event, med_id, user_id, name, age)
            await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
            await event.bot.send_message(
                user_id= user_id,
                text=resources.TEXT_TESTS_GET_DECODE_FINAL,
            )


        else:
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=2)

            await db.add_pending_notification(
                med_id=int(med_id),
                telegram_id= user_id,
                chat_id= chat_id,
                kind="decode"
            )
            await event.message.answer(text= resources.TEXT_TEST_IS_HAS_TRUE_DECODE_FALSE,
                                       attachments= [kb_tests_decode_empty()])

async def handle_get_med_id_consult(event:MessageCreated, name, age):
    chat_id, user_id = event.get_ids()
    med_id = event.message.body.text
    number = parse_int(med_id)

    if number is None:
        await event.message.answer(
            "❌ Нужно ввести целое число.\nПопробуйте ещё раз:"
        )
        return

    else:
        await db.create_dialog_user_with_med_id(user_id , med_id)
        await db.delete_neuro_dialog_states(user_id)
        doc_url = await db.get_test_results(number)

        if doc_url:
            await event.message.answer(text=resources.TEXT_NEW_MED_CONSULT_YES)
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=4)
            await after_tests_main_menu(event)
            await send_manager_get_consult(event, med_id, user_id, name, age)
        else:
            await event.message.answer(text=resources.TEXT_NEW_MED_CONSULT_NO, )
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=4)
            await after_tests_main_menu(event)

            await db.add_pending_notification(
                med_id=int(med_id),
                telegram_id=user_id,
                chat_id=chat_id,
                kind="decode"
            )
            await send_manager_get_consult(event, med_id, user_id, name, age)

async def handle_base_speak(event:MessageCreated, dialog, name, age):
    def add(role, msg):
        return dialog + f"\n{role}: {msg}"

    message = event.message
    chat_id, user_id = event.get_ids()
    text = message.body.text.strip()

    dialog = add("User", text)
    await db.append_answer(user_id, "User", text)

    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )

    wait_msg = await send_wait_emoji(event.bot, chat_id)

    raw = await open_ai_main.get_gpt_answer(
        BASE_SYSTEM_PROMPT,
        BASE_USER_PROMPT.format(dialog=dialog)
    )
    print(raw)
    answer = parse_base_answer(raw)

    if answer == "get_med":
        await db.set_neuro_dialog_states(user_id, resources.dialog_states["manager_collect"])

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        decision = parse_base_answer(raw)
        dialog = add("Assistant", decision)
        await db.append_answer(user_id, "Assistant", decision)

        await replace_wait_with_text(event.bot, chat_id, wait_msg, decision)
        return

    if answer == "get_boss":
        await db.set_neuro_dialog_states(user_id, resources.dialog_states["boss_collect"])

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=BOSS_COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        decision = parse_base_answer(raw)

        dialog = add("Assistant", decision)
        await db.append_answer(user_id, "Assistant", decision)

        await replace_wait_with_text(event.bot, chat_id, wait_msg, decision)
        return

    if answer == "get_analyses":
        await db.delete_neuro_dialog_states(user_id)
        await event.bot.send_message(
            user_id=user_id,
            text=resources.TEXT_MAKE_CHECK_UP,
            attachments= kb_check_up_start()
        )

    if answer == "get_results":
        med_id = await db.get_med_id(user_id)
        await db.delete_neuro_dialog_states(user_id)

        if med_id:
            doc_url = await db.get_test_results(int(med_id))
            is_tests_bad = await db.get_deviations(int(med_id))

            if doc_url:
                await event.bot.send_message(
                    user_id=user_id,
                    text=resources.TEXT_TESTS_IS_HAS_TRUE)

                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=5)
                await send_results_doc_and_text(event, doc_url)

                if is_tests_bad:
                    await event.bot.send_message(
                        user_id=user_id,
                        text=resources.TEXT_TESTS_IS_BAD,
                        attachments= kb_tests_decode()
                    )
                else:
                    await event.bot.send_message(
                        user_id=user_id,
                        text=resources.TEXT_TESTS_IS_GOOD)

                    await write_and_sleep(event=event,
                                          chat_id=chat_id,
                                          sleep_time=2)
                    await event.bot.send_message(
                        user_id=user_id,
                        text=resources.TEXT_AFTER_GOOD_TESTS,
                        attachments= kb_after_good_tests()
                    )
            else:
                await db.add_pending_notification(
                    med_id=int(med_id),
                    telegram_id=user_id,
                    chat_id=chat_id,
                    kind="decode"
                )

                await event.bot.send_message(
                    user_id=user_id,
                    text=resources.TEXT_TESTS_IS_HAS_FALSE)
                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=2)

                await event.bot.send_message(
                    user_id=user_id,
                    text=resources.TEXT_TESTS_MAIN_MENU,
                    attachments= [kb_tests_main_menu()]
                )

        else:
            await db.set_neuro_dialog_states(user_id, resources.dialog_states["get_med_id"])
            await event.bot.send_message(
                user_id=user_id,
                text=resources.TEXT_TESTS_GET_ID,
            )
        return

    if answer == "get_decode":
        med_id = await db.get_med_id(user_id)
        await db.delete_neuro_dialog_states(user_id)

        if med_id:
            decode = await db.get_test_decode(int(med_id))

            if decode:
                decode_message = f"Вот ваша расшифровка: {decode}"
                await event.bot.send_message(
                    user_id = user_id,
                    text=decode_message,
                )
                await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
                await write_and_sleep(event=event,
                                      chat_id=chat_id,
                                      sleep_time=3)

                await event.bot.send_message(
                    user_id = user_id,
                    text=resources.TEXT_GET_DECODE_COMPLETE_MESSAGE
                )

                await after_tests_main_menu(event)
                return

            await db.add_pending_notification(
                med_id=int(med_id),
                telegram_id=user_id,
                chat_id=chat_id,
                kind="decode"
            )

            await event.bot.send_message(
                user_id = user_id,
                text=resources.TEXT_TESTS_IS_HAS_TRUE_DECODE,
            )
            await write_and_sleep(event=event,
                                  chat_id=chat_id,
                                  sleep_time=3)

            await send_manager_get_decode(event= event,
                                          med_id= med_id,
                                          user_id= user_id,
                                          name= name,
                                          age= age)

            await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
            await event.bot.send_message(
                user_id = user_id,
                text=resources.TEXT_TESTS_GET_DECODE_FINAL,
                attachments= [kb_go_to_main_menu()]
            )

        else:
            await db.set_neuro_dialog_states(user_id, resources.dialog_states["get_med_id_decode"])
            await event.bot.send_message(
                user_id = user_id,
                text=resources.TEXT_TESTS_GET_ID,
            )
        return

    dialog = add("Assistant", answer)
    await db.append_answer(user_id, "Assistant", answer)

    await replace_wait_with_text(event.bot, chat_id, wait_msg, answer)
    return

async def handle_manager_collect(event:MessageCreated, dialog, state, name, age):
    def add(role, msg):
        return dialog + f"\n{role}: {msg}"

    message = event.message
    chat_id, user_id = event.get_ids()
    text = message.body.text.strip()
    dialog = add("User", text)
    await db.append_answer(user_id, "User", text)


    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )
    wait_msg = await send_wait_emoji(event.bot, chat_id)


    raw = await open_ai_main.get_gpt_answer(
        system_prompt=COLLECT_SYSTEM_PROMPT,
        user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
    )
    print(raw)
    result, data = pars_answer_and_data(raw)

    if result == "complete":
        if state == resources.dialog_states["med_collect"]:
            text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n просит помощи специалиста. У него следующая проблема :{data} \n\n(#Диалог_{user_id}). "
            await send_to_chat(event,user_id, text_to_manager)

            await complete_dialog(user_id= user_id,
                                  last_text="Дайте знать, если вам что то понадобится!")
            await replace_wait_with_text(
                event.bot, chat_id, wait_msg,
                "Спасибо. Я передал информацию специалисту. В ближайшее время с вами свяжутся."
            )

            await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
            await event.bot.send_action(
                chat_id=chat_id,
                action=SenderAction.TYPING_ON
            )
            await asyncio.sleep(2)

            await event.message.answer(text="Дайте знать, если вам что то понадобится")
        else:
            await replace_wait_with_text(
                event.bot, chat_id, wait_msg,
                "Спасибо.Я передал информацию менеджеру. В ближайшее время с вами свяжутся."
            )
            await complete_dialog(user_id= user_id,
                                  last_text="Дайте знать, если вам что то понадобится!")

            await event.bot.send_action(
                chat_id=chat_id,
                action=SenderAction.TYPING_ON
            )
            await asyncio.sleep(2)
            await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
            # Отправка в группу
            text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n просит помощи специалиста. У него следующая проблема :{data} \n\n(#Диалог_{user_id}). "
            await send_to_chat(event, user_id, text_to_manager)

            await event.message.answer(text="Дайте знать, если вам что то понадобится")
        return

    elif result == "back":
        msg_text = "Ок. Дайте знать, если вам что то понадобится"
        await complete_dialog(user_id= user_id, last_text=msg_text)
        await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
        await replace_wait_with_text(event.bot, chat_id, wait_msg, msg_text)
        return

    dialog = add("Assistant", result)
    await db.append_answer(user_id, "Assistant", result)
    await replace_wait_with_text(event.bot, chat_id, wait_msg, result)
    return

async def handle_boss_collect(event: MessageCreated, dialog, name, age):
    def add(role, msg):
        return dialog + f"\n{role}: {msg}"

    message = event.message
    chat_id, user_id = event.get_ids()
    text = message.body.text.strip()
    dialog = add("User", text)
    await db.append_answer(user_id, "User", text)

    wait_msg = await send_wait_emoji(event.bot, chat_id)

    raw = await open_ai_main.get_gpt_answer(
        system_prompt=BOSS_COLLECT_SYSTEM_PROMPT,
        user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
    )

    result, data = pars_answer_and_data(raw)

    if result == "complete":
        print("boss_complete")
        await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
        # Отправка в группу
        text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n обращается к руководству. У него следующая проблема :{data} \n\n(#Диалог_{user_id}). "
        await send_to_chat(event, user_id, text_to_manager)
        await replace_wait_with_text(event.bot, chat_id, wait_msg, "Спасибо. Ваше обращение передано руководству.")
        await complete_dialog(user_id= user_id,
                              last_text="Дайте знать, если вам что то понадобится!")
        return

    elif result == "back":
        msg_text = "Ок. Дайте знать, если вам что то понадобится"
        await complete_dialog(user_id= user_id,
                              last_text=msg_text)

        await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
        await replace_wait_with_text(event.bot, chat_id, wait_msg, msg_text)
        return

    dialog = add("Assistant", result)
    await db.append_answer(user_id, "Assistant", result)
    await replace_wait_with_text(event.bot, chat_id, wait_msg, result)
    return



async def handle_start_check_up(event:MessageCallback, context_data: MemoryContext):
    _, _ = event.get_ids()
    data = event.callback.payload
    msg = event.message

    if data == "сheck_up_start_back" :
        await event.bot.edit_message(
                message_id= event.message.body.mid,
                text= resources.TEXT_TESTS_MAIN_MENU,
                attachments= [tests_keyboards.kb_tests_main_menu()]
            )
    elif data == "сheck_up_start_add" :
        await choose_tests(event, context_data)
        await msg.delete()

async def handle_decode_yes_no(event:MessageCallback, name, age):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload

    med_id = await db.get_med_id(user_id)

    if data == "tests_decode_yes":
        await send_manager_get_decode(event= event,
                                      med_id= med_id,
                                      user_id=user_id,
                                      name= name,
                                      age = age)
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

async def handle_empty_decode(event:MessageCallback, name, age):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload

    med_id = await db.get_med_id(user_id)

    if data == "empty_decode_get_laborant":
        await db.set_neuro_dialog_states(user_id, resources.dialog_states["base_speak"])
        await write_and_sleep(event=event,
                              chat_id=chat_id,
                              sleep_time=3)
        await db.add_pending_notification(
            med_id=int(med_id),
            telegram_id=user_id,
            chat_id=chat_id,
            kind="decode"
        )

        await event.bot.send_message(user_id=user_id, text=resources.TEXT_TESTS_IS_HAS_TRUE_DECODE)
        await send_manager_get_decode(event, med_id,user_id, name, age)
        await write_and_sleep(event=event,
                              chat_id=chat_id,
                              sleep_time=3)

        await event.bot.send_message(
            user_id= user_id,
            text=resources.TEXT_TESTS_GET_DECODE_FINAL)


    elif data == "empty_decode_get_manager":
        await db.set_neuro_dialog_states(user_id, resources.dialog_states["manager_collect"])
        wait_msg = await send_wait_emoji(event.bot, chat_id)

        dialog = await db.get_dialog(user_id) or ""

        raw = await open_ai_main.get_gpt_answer(
            system_prompt=COLLECT_SYSTEM_PROMPT,
            user_prompt=BASE_USER_PROMPT.format(dialog=dialog)
        )
        decision = parse_base_answer(raw)

        await db.append_answer(user_id, "Assistant", decision)

        await replace_wait_with_text(
            event.bot, chat_id, wait_msg, decision
        )
        return

async def handle_after_good_tests_yes_no(event: MessageCallback):
    chat_id, user_id = event.get_ids()
    data = event.callback.payload
    message = event.message

    await write_and_sleep(event=event,
                          chat_id=chat_id,
                          sleep_time=5)
    await message.delete()

    if data == "after_good_tests_yes":
        await db.set_neuro_dialog_states(user_id=user_id,
                                         state=resources.dialog_states["after_tests_get_info"])

        await event.bot.send_message(
            user_id=user_id,
            text=resources.TEXT_QUESTION_AFTER_GOOD_TESTS,
        )

    elif data == "after_good_tests_no":
        await after_tests_main_menu(event=event)




async def send_manager_get_decode(event, med_id, user_id, name, age):
    doc_url = await db.get_test_results(int(med_id))
    doc_urls = split_urls_from_cell(doc_url)
    if doc_url:
        text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n просит расшифровать анализы.Вот номер его пробирки: {med_id}\nВот ссылки на анализы :\n{doc_urls} \n\n(#Диалог_{user_id})."
    else:
        text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n просит найти его анализы и сделать расшифровку. Вот номер его пробирки: {med_id}\n\n(#Диалог_{user_id})."
    await send_to_chat(event= event,
                       user_id= user_id,
                       message_text= text_to_manager)

async def send_manager_get_consult(event, med_id, user_id, name, age):
    doc_url = await db.get_test_results(int(med_id))
    doc_urls = split_urls_from_cell(doc_url)
    if doc_url:
        text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n просит консультацию по результатам анализов.Вот номер его пробирки: {med_id}\nВот ссылки на анализы :\n{doc_urls} \n\n(#Диалог_{user_id})."
    else:
        text_to_manager = f"Пользователь(Имя: {name}\n Возраст: {age})\n консультацию по результатам анализов.Анализы не найдены в таблице.\n Вот номер его пробирки: {med_id}\n\n(#Диалог_{user_id})."
    await send_to_chat(event=event,
                       user_id=user_id,
                       message_text=text_to_manager)




async def complete_dialog(user_id: int, last_text: str):
    await db.delete_dialog(user_id)
    await db.append_answer(user_id, "Assistant", last_text)