from pathlib import Path
from typing import Any
import datetime
from maxapi.context import MemoryContext
from maxapi.enums.sender_action import SenderAction
from maxapi.types import BotStarted
from maxapi.types import MessageCreated, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from max.max_bot_after_tests import max_bot_after_tests_main_menu
from utils import util_fins
import asyncio
from ai_agents.open_ai_main import get_gpt_answer
from utils.anketa_utils import *
from maxapi.types.attachments.buttons import MessageButton, CallbackButton
from max.max_bot_chat import max_bot_chat_manager
from db.anamnez import anamnez_db
from db.after_tests import after_tests_db

BACK_BUTTON = "⬅️ Назад"
image_path = Path(__file__).parent.parent / "images" / "image_andrey.jpg"


async def clear_all(event: MessageCreated):
    """Очистка всех данных пользователя и перезапуск стартового сценария"""
    chat_id, user_id = event.get_ids()
    await  event.bot.send_message(chat_id=chat_id, text= "Начат процесс очистки" )
    await asyncio.sleep(2)
    await anamnez_db.delete_user_full(user_id)
    await after_tests_db.delete_user_users_max(user_id)

    # Перезапускаем стартовый сценарий
    await start(event)

async def bot_started(event: BotStarted):
    chat_id, user_id = event.get_ids()
    args = event.payload

    # === 1. Новый пользователь ===
    ref_code = args if args else "base_url"
    await anamnez_db.add_user(user_id, name="", from_manager=ref_code)

    await anamnez_db.append_answer(
        telegram_id=user_id,
        text=f"Терапевт сказал: {resources.start_text}\n"
        )

    await anamnez_db.save_user_reply_state(
        user_id,
        manager_msg_id=resources.STATES_USERS_FINALS['start']
        )

        # Отправляем фото с текстом

    # with open(image_path, "rb") as image_file:
    #     buffer = image_file.read()  # читаем весь файл в память
    #     media = InputMediaBuffer(buffer=buffer, filename="image_andrey.jpg", type=UploadType.IMAGE)
    #
    #     await event.bot.send_message(
    #         chat_id = chat_id,
    #         text=resources.start_text,
    #         attachments=[media]
    #         )

    await event.bot.send_message(
        chat_id=chat_id,
        text=resources.start_text
    )

        # Переходим к следующему состоянию
    await anamnez_db.set_dialog_state(user_id, resources.dialog_states_dict["get_name"])
    return



async def start(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    # Получаем пользователя
    user = await anamnez_db.get_user(user_id)

    # Получаем анкету пользователя
    anketa = await anamnez_db.get_anketa(user_id=user_id)

    if anketa is None:
        # Если анкета не найдена — отправляем стартовое сообщение
        await anamnez_db.append_answer(
            telegram_id=user_id,
            text=f"Терапевт сказал: {resources.start_text}\n"
        )

        await anamnez_db.save_user_reply_state(
            user_id,
            manager_msg_id=resources.STATES_USERS_FINALS['start']
        )

        # with open(image_path, "rb") as image_file:
        #     buffer = image_file.read()  # читаем весь файл в память
        #     media = InputMediaBuffer(buffer=buffer, filename="image_andrey.jpg", type= UploadType.IMAGE)
        #
        #     await event.message.answer(
        #         text=resources.start_text,
        #         attachments=[media]
        #     )

        await event.message.answer(
            text=resources.start_text,
        )

        await anamnez_db.set_dialog_state(user_id, resources.dialog_states_dict["get_name"])
        return

    # === 3. Пользователь с анкетой ===
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="📝 Написать менеджеру", payload="reply_to_manager|0")
    )

    await event.message.answer(
        text=(
            f"Здравствуйте {user['name']}! Ожидаем вас на осмотре {anketa['osmotr_date']}!\n\n"
            f"Если у вас есть вопросы — вы можете задать их менеджеру, нажав на кнопку под сообщением."
        ),
        attachments=[builder.as_markup()]
    )

async def handle_text_message_anamnez(event: MessageCreated, context_data: MemoryContext):
    text = event.message.body.text
    if not text:
        return

    chat_id, user_id = event.get_ids()
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )

    await anamnez_db.append_answer(telegram_id=user_id, text=f"Пациент сказал:{text}\n")
    state = await anamnez_db.get_dialog_state(user_id)

    manager_msg_id = await anamnez_db.get_user_answer_state(user_id)
    if manager_msg_id is not None:
        # Ответ менеджеру → очищаем состояние
        await anamnez_db.delete_user_answer_state(user_id)

        # Отправляем сообщение в группу менеджеров
        await max_bot_chat_manager.send_to_chat(
            bot = event.bot,
            user_id= user_id,
            message_text=f"📨 Пользователь ответил:\n\n{text}\n\n\n#Диалог_{user_id}"
        )

        await event.message.answer("✅ Ваш ответ отправлен менеджеру.")
        return

    # FSM логика
    if state == resources.dialog_states_dict["anketa"]:
        await anketa_dialog(event, context_data)

    elif state == resources.dialog_states_dict['get_name']:
        await name_dialog(event)

    # elif state == resources.dialog_states_dict['medosmotr_in_company']:
    #     await medosmotr_in_company_dialog(event)

    elif state == resources.dialog_states_dict['new_branch_perfect_analyze']:
        await new_branch_dialog_fatigue(event, context_data)

    elif state == resources.dialog_states_dict['new_branch_overweight']:
        await new_branch_dialog_overweight(event, context_data)

    elif state == resources.dialog_states_dict['new_branch_blood_pressure']:
        await new_branch_dialog_blood_pressure(event, context_data)

    elif state == resources.dialog_states_dict['new_branch_another_problems']:
        await new_branch_dialog_another_problems(event)

    #
    # elif state == resources.dialog_states_dict['terapevt_consult']:
    #     await terapevt_consult_dialog(event)
    #
    # # elif state == resources.dialog_states_dict['change_anketa']:
    # #     await change_anketa_dialog(event)
    #
    # elif state == resources.dialog_states_dict['is_ready_to_consult']:
    #     await is_ready_to_consult_dialog(event)
    #
    # elif state == resources.dialog_states_dict['get_number']:
    #     await get_number_dialog(event)

    elif state == resources.dialog_states_dict['new_state']:
        user = await anamnez_db.get_user(user_id)
        anketa = await anamnez_db.get_anketa(user_id=user_id)
        name = user["name"]
        date = anketa["osmotr_date"]

        await event.message.answer(f"Приветствую {name}. До встречи на осмотре {date}")

    else:
        print("handle_text_message - else")


async def name_dialog(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)

    user = await anamnez_db.get_user(user_id)
    text = event.message.body.text
    name = util_fins.normalize_name(text)

    if user is None:
        await anamnez_db.add_user(
            user_id=user_id,
            name= name,
            from_manager= "base_url",
        )
    else:
        await anamnez_db.add_user(
            user_id=user_id,
            name=name,
            from_manager=user["from_manager"] or "base_url",
            register_date=user["register_date"] or "",
        )

    await anamnez_db.set_dialog_state(user_id, resources.dialog_states_dict["anketa"])
    await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
    await asyncio.sleep(1)

    # Запускаем анкету
    await start_anketa(event)

async def start_anketa(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    # 1️⃣ Сбрасываем состояние анкеты в БД
    await anamnez_db.set_user_state(user_id, {
        "position": 0,
        "answers": [],
        "mode": "anketa_osmotr"
    })

    # 2️⃣ Устанавливаем общий dialog_state (если ты его используешь)
    await anamnez_db.set_dialog_state(
        user_id,
        resources.dialog_states_dict["anketa"]
    )

    # 3️⃣ Получаем список вопросов
    questions = resources.QUESTIONS

    # 4️⃣ Отправляем первый вопрос
    await ask_question(event, pos=0, questions=questions)

async def new_branch_dialog_fatigue(event: MessageCreated, context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    dialog = await anamnez_db.get_dialog(user_id)
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )
    user_prompt = prompts.user_prompt_agent_fatigue.format(dialog = dialog)

    agent_text = await get_gpt_answer(system_prompt= prompts.system_prompt_agent_fatique,
                                      user_prompt= user_prompt,
                                      bot= event.bot)
    agent_answer = util_fins.parse_agent_fatigue_answer(agent_text)


    if agent_answer is None:
        await event.message.answer(text="Что то не так, попробуйте вести ответ заново через минуту!")
    elif agent_answer == "all_right":
        await anamnez_db.delete_dialog(user_id)

        await anamnez_db.append_answer(telegram_id=user_id,
                                       text=f"Медицинский ассистент сказал: {resources.text_new_branch_another_problems}")
        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_branch_another_problems"]
        )

        await event.message.answer(text= resources.text_new_branch_another_problems)


    elif agent_answer == "complete":
        context = await context_data.get_data()
        has_overweight = context.get("has_overweight")
        has_blood_pressure = context.get("has_blood_pressure")
        answer_text = f"{resources.text_new_branch_fatigue_complete}"
        if has_overweight:
            answer_text += "\nВ анкете были выявлены признаки избыточного веса. Рекомендуем также добавить чек-ап «Лишний вес»"
        if has_blood_pressure:
            answer_text += "\nВ анкете было выявлено повышенное давление. Рекомендуем также добавить чек-ап «Липидный обмен»"

        answer_text += "\nВыберите чек-ап из списка и сделайте шаг к своему здоровью."

        await anamnez_db.append_answer(telegram_id= user_id, text = f"Медицинский ассистент сказал: {answer_text}")
        await event.message.answer(text=answer_text)
        await asyncio.sleep(4)

        await event.message.answer(text= resources.text_check_up_url)

        await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
        await asyncio.sleep(3)

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(CallbackButton(text = "Да", payload="dop_yes"),
                                     CallbackButton(text = "Нет", payload="dop_no"))
        await event.message.answer(
            text= resources.text_new_branch_go_to_tests,
            attachments= [keyboard_builder.as_markup()]
            )

        
    else:
        await anamnez_db.append_answer(telegram_id= user_id, text = f"Медицинский ассистент сказал: {agent_answer}")
        await event.message.answer(text= agent_answer)

async def new_branch_dialog_overweight(event: MessageCreated,context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    dialog = await anamnez_db.get_dialog(user_id)
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )
    user_prompt = prompts.user_prompt_agent_overweight.format(dialog = dialog)
    agent_text = await get_gpt_answer(system_prompt= prompts.system_prompt_agent_overweight,
                                      user_prompt= user_prompt,
                                      bot= event.bot)
    agent_answer = util_fins.parse_agent_fatigue_answer(agent_text)

    if agent_answer is None:
        await event.message.answer(text="Что то не так, попробуйте вести ответ заново через минуту!")
    elif agent_answer == "all_right":
        await anamnez_db.delete_dialog(user_id)

        await anamnez_db.append_answer(
            telegram_id=user_id,
            text=f"Медицинский ассистент сказал:{resources.text_new_branch_perfect_analyze_short}"
        )

        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_branch_perfect_analyze"]
        )

        await event.message.answer(
            resources.text_new_branch_perfect_analyze_short
        )


    elif agent_answer == "complete":
        context = await context_data.get_data()
        has_blood_pressure = context.get("has_blood_pressure")
        answer_text = f"{resources.text_new_branch_overweight_complete}"
        if has_blood_pressure:
            answer_text += "\nВ анкете было выявлено повышенное давление. Рекомендуем также добавить чек-ап «Липидный обмен»"

        answer_text += "\nВыберите чек-ап из списка и сделайте шаг к своему здоровью."

        await anamnez_db.append_answer(telegram_id=user_id,
                                       text=f"Медицинский ассистент сказал: {answer_text}")
        await event.message.answer(text=answer_text)
        await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
        await asyncio.sleep(4)

        await event.message.answer(text=resources.text_check_up_url)

        await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
        await asyncio.sleep(3)

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(CallbackButton(text="Да", payload="dop_yes"),
                             CallbackButton(text="Нет", payload="dop_no"))
        await event.message.answer(
            text=resources.text_new_branch_go_to_tests,
            attachments=[keyboard_builder.as_markup()]
        )


    else:
        await anamnez_db.append_answer(telegram_id=user_id, text=f"Медицинский ассистент сказал: {agent_answer}")
        await event.message.answer(text=agent_answer)

async def new_branch_dialog_blood_pressure(event: MessageCreated, context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    dialog = await anamnez_db.get_dialog(user_id)
    await event.bot.send_action(chat_id=chat_id,action=SenderAction.TYPING_ON)

    user_prompt = prompts.user_prompt_agent_blood_pressure.format(dialog = dialog)
    agent_text = await get_gpt_answer(system_prompt= prompts.system_prompt_agent_blood_pressure,
                                      user_prompt= user_prompt,
                                      bot= event.bot)
    agent_answer = util_fins.parse_agent_fatigue_answer(agent_text)

    if agent_answer is None:
        await event.message.answer(text="Что то не так, попробуйте вести ответ заново через минуту!")
    elif agent_answer == "all_right":
        await anamnez_db.delete_dialog(user_id)
        await anamnez_db.append_answer(
            telegram_id=user_id,
            text=f"Медицинский ассистент сказал:{resources.text_new_branch_perfect_analyze_short}"
        )

        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_branch_perfect_analyze"]
        )
        await anamnez_db.delete_dialog(user_id)

        await event.message.answer(
            resources.text_new_branch_perfect_analyze_short
        )


    elif agent_answer == "complete":
        context = await context_data.get_data()
        has_overweight = context.get("has_overweight")
        answer_text = f"{resources.text_new_branch_blood_pressure_complete}"
        if has_overweight:
            answer_text += "\nВ анкете были выявлены признаки избыточного веса. Рекомендуем также добавить чек-ап «Лишний вес»"
        answer_text += "\nВыберите чек-ап из списка и сделайте шаг к своему здоровью."

        await anamnez_db.append_answer(telegram_id=user_id,
                                       text=f"Медицинский ассистент сказал: {answer_text}")
        await event.message.answer(text= answer_text)
        await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
        await asyncio.sleep(4)

        await event.message.answer(text=resources.text_check_up_url)

        await event.bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
        await asyncio.sleep(3)

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(CallbackButton(text="Да", payload="dop_yes"),
                             CallbackButton(text="Нет", payload="dop_no"))
        await event.message.answer(
            text=resources.text_new_branch_go_to_tests,
            attachments=[keyboard_builder.as_markup()]
        )

    else:
        await anamnez_db.append_answer(telegram_id=user_id, text=f"Медицинский ассистент сказал: {agent_answer}")
        await event.message.answer(text=agent_answer)

async def new_branch_dialog_another_problems(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    dialog = await anamnez_db.get_dialog(user_id)
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )
    user_prompt = prompts.user_prompt_agent_another_problems.format(dialog = dialog)
    agent_text = await get_gpt_answer(system_prompt= prompts.system_prompt_agent_another_problems,
                                      user_prompt= user_prompt,
                                      bot= event.bot)
    agent_answer = util_fins.parse_agent_fatigue_answer(agent_text)

    if agent_answer is None:
        await event.message.answer(text="Что то не так, попробуйте вести ответ заново через минуту!")

    elif agent_answer == "all_right":
        await event.message.answer(text=resources.text_new_branch_another_problem_all_right)
        await asyncio.sleep(3)

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(CallbackButton(text="Да", payload="dop_yes"),
                             CallbackButton(text="Нет", payload="dop_no"))
        await event.message.answer(
            text=resources.text_new_branch_go_to_tests,
            attachments=[keyboard_builder.as_markup()]
        )

    elif agent_answer == "complete":
        user_data = await anamnez_db.get_user(user_id=user_id)
        await event.message.answer(text=resources.text_new_branch_another_problem_complete)

        text_to_manager = (
            f"Пользователь: {user_data['name']} (ID- {user_id}).\n"
            f"Оставил жалобу:\n{dialog}"
            f"\n\n\n#Диалог_{user_id}"
        )


        await max_bot_chat_manager.send_to_chat(event.bot, user_id, text_to_manager)
        await asyncio.sleep(3)

        await event.message.answer(text=resources.text_new_branch_another_problem_all_right)
        await asyncio.sleep(3)

        keyboard_builder = InlineKeyboardBuilder()
        keyboard_builder.row(CallbackButton(text="Да", payload="dop_yes"),
                             CallbackButton(text="Нет", payload="dop_no"))
        await event.message.answer(
            text=resources.text_new_branch_go_to_tests,
            attachments=[keyboard_builder.as_markup()]
        )

        # await max_bot_after_tests_main_menu.after_tests_main_menu(event)

    else:
        await anamnez_db.append_answer(telegram_id=user_id, text=f"Медицинский ассистент сказал: {agent_answer}")
        await event.message.answer(text=agent_answer)

# async def anketa_dialog(event: MessageCreated):
#     chat_id, user_id = event.get_ids()
#     text = event.message.body.text
#
#     # Имитация печати
#     await event.bot.send_action(
#         chat_id=chat_id,
#         action=SenderAction.TYPING_ON
#     )
#
#     # Получаем состояние из БД
#     state = await anamnez_db.get_user_state(user_id)
#     pos = state["position"]
#     answers = state["answers"]
#     mode = state["mode"]
#
#     # Определяем набор вопросов
#     if mode == "anketa_osmotr":
#         questions = resources.QUESTIONS
#         questions_small = resources.QUESTIONS_SMALL
#     else:
#         questions = resources.QUESTIONS_IF_NOT_OSMOTR
#         questions_small = resources.QUESTIONS_SMALL_IF_NOT_OSMOTR
#
#     # ===== КНОПКА НАЗАД =====
#     if text == BACK_BUTTON:
#         if pos > 0:
#             pos -= 1
#             if answers:
#                 answers.pop()
#
#             await anamnez_db.set_user_state(user_id, {
#                 "position": pos,
#                 "answers": answers,
#                 "mode": mode
#             })
#
#         await ask_question(event, pos, questions)
#         return
#
#     # ===== ВАЛИДАЦИЯ =====
#     result = await util_fins.validate_anketa_questions(
#         position=pos,
#         user_say=text,
#         user_id= user_id,
#         bot= event.bot
#     )
#
#     if pos != 12:
#         if result == "empty":
#             await event.message.answer(
#                 "Для ответа выберите один из вариантов, нажав на соответствующую кнопку!"
#             )
#             return
#
#         if result != "complete":
#             await event.message.answer(result)
#             return
#         answers.append(text)
#
#
#
#     if pos == 12:
#         if "complete" in result:
#             answers.append(result)
#         else:
#             await event.message.answer(result)
#             return
#
#
#
#
#     pos += 1
#
#     # ===== ЕЩЁ ЕСТЬ ВОПРОСЫ =====
#     if pos < len(questions):
#         await anamnez_db.set_user_state(user_id, {
#             "position": pos,
#             "answers": answers,
#             "mode": mode
#         })
#
#         await ask_question(event, pos, questions)
#         return
#
#     # ===== АНКЕТА ЗАВЕРШЕНА =====
#
#     # Сохраняем финальное состояние
#     await anamnez_db.set_user_state(user_id, {
#         "position": pos,
#         "answers": answers,
#         "mode": None
#     })
#
#     await anamnez_db.save_user_reply_state(
#         user_id,
#         manager_msg_id=resources.STATES_USERS_FINALS['final_anketa']
#     )
#
#     await event.message.answer("⏳ Анализирую анкету...")
#
#     try:
#         # Сохраняем анкету в БД
#         await add_to_anketa(event, answers)
#
#         # Формируем текст анкеты
#         anketa_text = "\n".join(
#             f"{i + 1}. {q} — {a}"
#             for i, (q, a) in enumerate(zip(questions_small, answers))
#         )
#
#         # Запрос к GPT
#         user_prompt = prompts.user_prompt_new_rec_tests.format(
#             anketa=anketa_text
#         )
#
#         recs = await get_gpt_answer(
#             system_prompt=prompts.system_prompt_new_rec_tests,
#             user_prompt=user_prompt,
#             bot=event
#         )
#
#         risks, recommendations_list, rec_text = ai_utils.extract_recs(recs)
#
#         # ===== ЕСЛИ ЕСТЬ РЕКОМЕНДАЦИИ =====
#         if recommendations_list:
#
#             await event.message.answer(
#                 f"Проанализировав ваши ответы, я выявил некоторые риски:\n{risks}\n"
#             )
#
#             await asyncio.sleep(5)
#
#             await event.message.answer(
#                 "На основе этого анализа я сформировал ПЕРСОНАЛЬНУЮ РЕКОМЕНДАЦИЮ.\n"
#                 f"Вам полезно пройти комплекс исследований:\n{rec_text}"
#             )
#
#             await asyncio.sleep(2)
#
#             await event.message.answer(
#                 "Также вы можете выбрать любой из представленных комплексов услуг.\n"
#                 "Ознакомиться можно по ссылке:\n"
#                 f"https://telegra.ph/CHek-apy-po-laboratorii-OOO-CHelovek-02-06?ver={int(datetime.now().timestamp())}"
#             )
#
#             await asyncio.sleep(2)
#             keyboard_builder = InlineKeyboardBuilder()
#             keyboard_builder.row(CallbackButton(text = "Да", payload="dop_yes"),
#                                 CallbackButton(text = "Нет", payload="dop_no"))
#
#             await event.message.answer(
#                 resources.by_dop_tests_or_not_text,
#                 attachments= [keyboard_builder.as_markup()]
#             )
#
#         # ===== ЕСЛИ РЕКОМЕНДАЦИЙ НЕТ =====
#         else:
#             await anamnez_db.append_answer(
#                 telegram_id=user_id,
#                 text=f"Терапевт сказал:{resources.is_has_complaint_text}"
#             )
#
#             await anamnez_db.set_dialog_state(
#                 user_id,
#                 resources.dialog_states_dict["is_has_complaint"]
#             )
#
#             await event.message.answer(
#                 resources.is_has_complaint_text
#             )
#
#     finally:
#         # Удаляем сообщение ожидания
#         try:
#             # await event.bot.delete_message(
#             #     chat_id=chat_id,
#             #     message_id=wait_msg.id
#             # )
#             print("E")
#         except Exception:
#             pass

async def anketa_dialog(event: MessageCreated,  context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    text = event.message.body.text

    # Имитация печати
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )

    # Получаем состояние из БД
    state = await anamnez_db.get_user_state(user_id)
    pos = state["position"]
    answers = state["answers"]
    mode = state["mode"]

    # Определяем набор вопросов
    if mode == "anketa_osmotr":
        questions = resources.QUESTIONS
        questions_small = resources.QUESTIONS_SMALL
    else:
        questions = resources.QUESTIONS_IF_NOT_OSMOTR
        questions_small = resources.QUESTIONS_SMALL_IF_NOT_OSMOTR

    # ===== КНОПКА НАЗАД =====
    if text == BACK_BUTTON:
        if pos > 0:
            pos -= 1
            if answers:
                answers.pop()

            await anamnez_db.set_user_state(user_id, {
                "position": pos,
                "answers": answers,
                "mode": mode
            })

        await ask_question(event, pos, questions)
        return

    # ===== ВАЛИДАЦИЯ =====
    result = await util_fins.validate_anketa_questions(
        position=pos,
        user_say=text,
        user_id= user_id,
        bot= event.bot
    )

    if pos != 12:
        if result == "empty":
            await event.message.answer(
                "Для ответа выберите один из вариантов, нажав на соответствующую кнопку!"
            )
            return

        if result != "complete":
            await event.message.answer(result)
            return
        answers.append(text)



    if pos == 12:
        if "complete" in result:
            answers.append(result)
        else:
            await event.message.answer(result)
            return

    pos += 1

    # ===== ЕЩЁ ЕСТЬ ВОПРОСЫ =====
    if pos < len(questions):
        await anamnez_db.set_user_state(user_id, {
            "position": pos,
            "answers": answers,
            "mode": mode
        })

        await ask_question(event, pos, questions)
        return

    # ===== АНКЕТА ЗАВЕРШЕНА =====

    # Сохраняем финальное состояние
    await anamnez_db.set_user_state(user_id, {
        "position": pos,
        "answers": answers,
        "mode": None
    })

    await anamnez_db.save_user_reply_state(
        user_id,
        manager_msg_id=resources.STATES_USERS_FINALS['final_anketa']
    )

    await event.message.answer("⏳ Анализирую анкету...")

    try:
        # Сохраняем анкету в БД
        await add_to_anketa(event, answers)

        # Формируем текст анкеты
        anketa_text = "\n".join(
            f"{i + 1}. {q} — {a}"
            for i, (q, a) in enumerate(zip(questions_small, answers))
        )

        # Запрос к GPT
        user_prompt = prompts.user_prompt_new_analyze.format(
            anketa=anketa_text
        )

        analyze_gpt_result = await get_gpt_answer(
            system_prompt=prompts.system_prompt_new_analyze,
            user_prompt=user_prompt,
            bot=event
        )

        analyze_result = util_fins.parse_health_issues(analyze_gpt_result)
        has_overweight = any(i["type"] == "overweight" for i in analyze_result)
        has_blood_pressure = any(i["type"] == "blood_pressure" for i in analyze_result)

        if len(analyze_result) > 0:
            await context_data.set_state("rec_tests")
            await context_data.set_data({
                "has_overweight": has_overweight,
                "has_blood_pressure": has_blood_pressure,
            })

        if len(analyze_result) == 0:
            await anamnez_db.append_answer(
                telegram_id=user_id,
                text=f"Терапевт сказал:{resources.text_new_branch_perfect_analyze}"
            )

            await anamnez_db.set_dialog_state(
                user_id,
                resources.dialog_states_dict["new_branch_perfect_analyze"]
            )

            await event.message.answer(
                resources.text_new_branch_perfect_analyze
            )

        elif has_overweight:
            await anamnez_db.append_answer(
                telegram_id=user_id,
                text=f"Терапевт сказал:{resources.text_new_branch_overweight}"
            )

            await anamnez_db.set_dialog_state(
                user_id,
                resources.dialog_states_dict["new_branch_overweight"]
            )

            await event.message.answer(
                resources.text_new_branch_overweight
            )

        elif has_blood_pressure:
            await anamnez_db.append_answer(
                telegram_id=user_id,
                text=f"Терапевт сказал:{resources.text_new_branch_blood_pressure}"
            )

            await anamnez_db.set_dialog_state(
                user_id,
                resources.dialog_states_dict["new_branch_blood_pressure"]
            )

            await event.message.answer(
                resources.text_new_branch_blood_pressure
            )


    finally:
        # Удаляем сообщение ожидания
        try:
            # await event.bot.delete_message(
            #     chat_id=chat_id,
            #     message_id=wait_msg.id
            # )
            print("E")
        except Exception:
            pass

async def ask_question(event: MessageCreated, pos: int, questions: list[str]):
    chat_id, user_id = event.get_ids()

    # Имитация печати
    await event.bot.send_action(
        chat_id=chat_id,
        action=SenderAction.TYPING_ON
    )

    # Текст вопроса
    text = questions[pos]

    # Логируем в историю диалога
    await anamnez_db.append_answer(
        telegram_id=user_id,
        text=f"Терапевт сказал:{text}\n"
    )

    keyboard_builder = InlineKeyboardBuilder()

    # ===== Специальные вопросы с вариантами =====

    if pos == 5:
        text, buttons = question_smoke()

    elif pos == 6:
        text, buttons = question_alko()

    elif pos == 7:
        text, buttons = question_physical()

    elif pos == 8:
        text, buttons = question_hyperton()

    elif pos == 9:
        text, buttons = question_dark_in_eyes()

    elif pos == 10:
        text, buttons = question_sugar()

    elif pos == 11:
        text, buttons = question_sustavi()

    else:
        buttons = None

    # ===== Формирование клавиатуры =====

    if buttons:
        for btn_in_line in buttons:
            keyboard_builder.row(
                *[
                    MessageButton(text=btn)
                    for btn in btn_in_line
                ]
            )

    # Кнопка "Назад"
    if 0 < pos < 5 or pos == 12:
        keyboard_builder.row(
            MessageButton(
                text=BACK_BUTTON
            )
        )

    # Отправка
    await asyncio.sleep(1)

    if buttons or pos > 0:
        await event.message.answer(
            text=text,
            attachments=[keyboard_builder.as_markup()]
        )
    else:
        await event.message.answer(text=text)

async def add_to_anketa(event: MessageCreated, answers: list[Any]):
    chat_id, user_id = event.get_ids()
    # Безопасность: проверка длины анкеты
    if len(answers) < 13:
        raise ValueError("Недостаточно ответов для сохранения анкеты")
    print(answers)

    # В текущем коде обе ветки одинаковые.
    # Если позже появится различие — логика уже готова.
    await anamnez_db.add_or_update_anketa(
        user_id=user_id,
        organization_or_inn=answers[0],
        osmotr_date=answers[1],
        age=answers[2],
        weight=answers[3],
        height=answers[4],
        smoking=answers[5],
        alcohol=answers[6],
        physical_activity=answers[7],
        hypertension=answers[8],
        darkening_of_the_eyes=answers[9],
        sugar=answers[10],
        joint_pain=answers[11],
        chronic_diseases=answers[12],
    )


async def handle_dop_analizy(event: MessageCallback,  context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    payload = event.callback.payload

    if payload == "dop_yes":

        await anamnez_db.save_user_reply_state(
            user_id,
            manager_msg_id=resources.STATES_USERS_FINALS["dop_true"]
        )

        await choose_tests(event,context_data)

    elif payload == "dop_no":

        await anamnez_db.save_user_reply_state(
            user_id,
            manager_msg_id=resources.STATES_USERS_FINALS["dop_false"]
        )

        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_state"]
        )

        # --- создаём клавиатуру ---
        keyboard_builder = InlineKeyboardBuilder()

        keyboard_builder.row(
            CallbackButton(
                text="Хочу сдать анализы",
                payload="dopDop_yes"
            )
        )

        keyboard_builder.row(
            CallbackButton(
                text="Спасибо, но нет",
                payload="dopDop_no"
            ))

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.get_tests_answer_false_text,
            attachments =[keyboard_builder.as_markup()]
        )

async def handle_dopDop_analizy(event:MessageCallback, context_data: MemoryContext):
    chat_id, user_id = event.get_ids()
    payload = event.callback.payload

    message_id = event.message.body.mid

    # Удаляем сообщение с кнопками
    await event.bot.delete_message(
        message_id=message_id
    )

    # ===== ЛОГИКА =====

    if payload == "dopDop_yes":

        await anamnez_db.save_user_reply_state(
            user_id,
            manager_msg_id=resources.STATES_USERS_FINALS["dop_dop_true"]
        )

        await choose_tests(event,context_data)

    elif payload == "dopDop_no":

        await anamnez_db.save_user_reply_state(
            user_id,
            manager_msg_id=resources.STATES_USERS_FINALS["dop_dop_false"]
        )

        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_state"]
        )

        anketa = await anamnez_db.get_anketa(user_id=user_id)
        date = anketa["osmotr_date"]

        await event.bot.send_message(
            chat_id=chat_id,
            text="Спасибо за ответ! Вы также можете выбрать подходящие исследования непосредственно перед осмотром."
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=f"Будем ждать Вас на осмотре {date}"
        )

        await asyncio.sleep(3)

        return "after_tests_start"
    return None


def build_tests_keyboard(selected_indexes: set[int]):
    keyboard_builder = InlineKeyboardBuilder()
    row_buffer = []

    for idx, test in enumerate(resources.TESTS):

        text = f"✅ {test}" if idx in selected_indexes else test
        button = CallbackButton(
            text=text,
            payload=f"toggle:{idx}"
        )

        if len(test) > 15:
            if row_buffer:
                keyboard_builder.row(*row_buffer)
                row_buffer = []
            keyboard_builder.row(button)
        else:
            row_buffer.append(button)
            if len(row_buffer) == 2:
                keyboard_builder.row(*row_buffer)
                row_buffer = []

    if row_buffer:
        keyboard_builder.row(*row_buffer)

    keyboard_builder.row(
        CallbackButton(text="ГОТОВО", payload="done")
    )
    keyboard_builder.row(
        CallbackButton(text="Не хочу проходить обследования", payload="skip_tests")
    )

    return keyboard_builder.as_markup()

async def choose_tests(event: MessageCallback, context_data: MemoryContext):
    chat_id, user_id = event.get_ids()


    await context_data.set_state("SELECTING_TESTS")
    await context_data.set_data({
        "selected_tests": set(),
        "tests_message_id": None,
        "dop_message_id": None
    })

    sent = await event.bot.send_message(
        chat_id=chat_id,
        text=resources.choose_tests_text,
        attachments= [build_tests_keyboard(set())]
    )

    await context_data.update_data(tests_message_id=sent.message.body.mid)

async def handle_toggle(event:MessageCallback, context_data: MemoryContext):
    state = await context_data.get_state()
    chat_id, user_id = event.get_ids()
    if state != "SELECTING_TESTS":
        return None

    data = await context_data.get_data()
    selected = data.get("selected_tests", set())
    message_id = data.get("tests_message_id")

    payload = event.callback.payload


    # --- TOGGLE ---
    if payload.startswith("toggle:"):

        idx = int(payload.split(":")[1])

        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)

        await context_data.update_data(selected_tests=selected)
        await event.message.edit(text= resources.choose_tests_text,
                                 attachments=[build_tests_keyboard(selected)])


    # --- DONE ---
    elif payload == "done":

        if not selected:
            await event.bot.send_message(
                chat_id= chat_id,
                text="Выберите хотя бы один анализ."
            )
            return None

        chosen_names = [resources.TESTS[i] for i in selected]
        chosen_str = ", ".join(chosen_names)

        # получаем данные из БД (они постоянные)
        user_data = await anamnez_db.get_user(user_id=user_id)
        anketa = await anamnez_db.get_anketa(user_id=user_id)
        osmotr_date = anketa["osmotr_date"] if anketa["osmotr_date"] else "ошибка получения даты"
        inn_organization = anketa["organization_or_inn"] if anketa["organization_or_inn"] else "ошибка получения ИНН"

        # сохраняем финальный выбор в БД
        await anamnez_db.add_user(
            user_id=user_id,
            name=user_data['name'],
            is_medosomotr=user_data['is_medosomotr'],
            register_date=user_data['register_date'],
            from_manager=user_data['from_manager'],
            privacy_policy_date=user_data['privacy_policy_date'],
            get_dop_tests=chosen_str
        )

        # сообщение менеджеру
        text_to_manager = (
            f"Пользователь: {user_data['name']} (ID- {user_id}).\n"
            f"Дата осмотра: {osmotr_date}\n"
            f"ИНН организаци: {inn_organization}\n"
            f"Планирует пройти дополнительные обследования.\n\n"
            f"Обследования: {chosen_str}"
        )

        await max_bot_chat_manager.send_to_chat(event.bot, user_id, text_to_manager)

        # удаляем сообщение с кнопками
        try:
            await event.bot.delete_message(
                message_id=message_id
            )
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")

        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_state"]
        )

        text, price = await util_fins.get_list_and_price(
            list_tests=chosen_names,
            tests_price=resources.TESTS_PRICE
        )

        await anamnez_db.save_user_reply_state(
            user_id,
            manager_msg_id=resources.STATES_USERS_FINALS['victory']
        )

        builder = InlineKeyboardBuilder()
        builder.row(CallbackButton(text="Оплатить онлайн", payload="pay_yes"),
                    CallbackButton(text="Оплатить позже", payload="pay_no"))
        await context_data.clear()
        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.get_final_text_tests_with_price2(
                tests=text,
                price=price
            ),
            attachments= [builder.as_markup()]
        )

    elif payload == "skip_tests":
        try:
            await event.bot.delete_message(
                message_id=message_id
            )
        except Exception as e:
            print(f"Ошибка удаления сообщения: {e}")

        return "after_tests_start"

    return None

async def handle_pay(event:MessageCallback):
    chat_id, user_id = event.get_ids()
    payload = event.callback.payload

    if payload == "pay_yes":
        await anamnez_db.set_privacy_policy_date(user_id= user_id, value= "pay_yes")

        await event.bot.send_message(
            chat_id=chat_id,
            text= resources.text_new_branch_handle_pay_yes
        )
        await event.bot.send_action(
            chat_id=chat_id,
            action=SenderAction.TYPING_ON
        )

        await asyncio.sleep(2)
        await max_bot_after_tests_main_menu.after_tests_main_menu(event)

    elif payload == "pay_no":
        await anamnez_db.set_privacy_policy_date(user_id= user_id, value= "pay_no")
        await event.bot.send_message(
            chat_id=chat_id,
            text= resources.text_new_branch_handle_pay_no
        )
        await event.bot.send_action(
            chat_id=chat_id,
            action=SenderAction.TYPING_ON
        )

        await asyncio.sleep(2)
        await max_bot_after_tests_main_menu.after_tests_main_menu(event)


async def handle_consent(event: MessageCallback, payload: str):
    chat_id, user_id = event.get_ids()

    user_data = await anamnez_db.get_user(user_id=user_id)

    if payload == "consent_yes":
        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["get_number"]
        )

        await anamnez_db.add_user(
            user_id=user_id,
            name=user_data['name'],
            is_medosomotr=user_data['is_medosomotr'],
            phone=user_data["phone"],
            register_date=user_data['register_date'],
            from_manager="from_manager",
            privacy_policy_date=datetime.datetime.now(datetime.UTC),
        )

        await anamnez_db.append_answer(
            telegram_id=user_id,
            text=f"Менеджер сказал: {resources.get_number_text}"
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.privacy_policy_true
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.get_number_text
        )

    elif payload == "consent_no":
        await anamnez_db.set_dialog_state(
            user_id,
            resources.dialog_states_dict["new_state"]
        )

        await anamnez_db.add_user(
            user_id=user_id,
            name=user_data['name'],
            is_medosomotr=user_data['is_medosomotr'],
            phone=user_data["phone"],
            register_date=user_data['register_date'],
            from_manager="from_manager",
            privacy_policy_date=datetime.datetime.now(datetime.UTC),
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.privacy_policy_false
        )

        await event.bot.send_message(
            chat_id=chat_id,
            text="Спасибо за ответы. До встречи на медосмотре!"
        )