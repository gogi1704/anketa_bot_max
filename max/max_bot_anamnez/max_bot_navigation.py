from pathlib import Path
from typing import Any
import datetime
from maxapi import Bot
from maxapi.context import MemoryContext
from maxapi.enums.sender_action import SenderAction
from maxapi.types import BotStarted
from maxapi.types import MessageCreated, MessageCallback
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from max.max_bot_after_tests.max_bot_after_tests_main_menu import after_tests_main_menu
from utils import util_fins
import asyncio
from ai_agents.open_ai_main import get_gpt_answer
from ai_agents import ai_utils
from utils.anketa_utils import *
from maxapi.types.attachments.buttons import MessageButton, CallbackButton
from max.max_bot_chat import max_bot_chat_manager
from db.anamnez import anamnez_db
from db.after_tests import after_tests_db

BACK_BUTTON = "⬅️ Назад"
image_path = Path(__file__).parent.parent / "images" / "image_andrey.jpg"


async def clear_all(event: MessageCreated, bot: Bot):
    """Очистка всех данных пользователя и перезапуск стартового сценария"""
    # Показываем «печатает…»
    chat_id, user_id = event.get_ids()
    await event.bot.send_action(
        chat_id= chat_id,
        action= SenderAction.TYPING_ON
    )

    await anamnez_db.delete_dialog(user_id)
    await anamnez_db.delete_user(user_id)
    await anamnez_db.delete_user_reply_state(user_id)
    await anamnez_db.delete_anketa(user_id)

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
    user_is_after_tests = await after_tests_db.get_user_state(user_id)

    if user_is_after_tests:
        await after_tests_main_menu(event)
        return
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

async def handle_text_message(event: MessageCreated):
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
            event = event,
            user_id= user_id,
            message_text=f"📨 Пользователь ответил:\n\n{text}\n\n\n#Диалог_с_{user_id}"
        )

        await event.message.answer("✅ Ваш ответ отправлен менеджеру.")
        return

    # FSM логика
    if state == resources.dialog_states_dict["anketa"]:
        await anketa_dialog(event)

    elif state == resources.dialog_states_dict['get_name']:
        await name_dialog(event)

    # elif state == resources.dialog_states_dict['medosmotr_in_company']:
    #     await medosmotr_in_company_dialog(event)

    # elif state == resources.dialog_states_dict['is_has_complaint']:
    #     await is_has_complaint_dialog(event)
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
            name= "default",
            from_manager= "base_url",
        )
    else:
        await anamnez_db.add_user(
            user_id=user_id,
            name=name,
            from_manager=user["from_manager"],
            register_date=user["register_date"],
        )


    await anamnez_db.set_dialog_state(user_id, resources.dialog_states_dict["anketa"])

    answer = resources.second_text.format(user_name=name, user_id=user_id)
    msg = await event.message.answer(text=answer)

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

async def anketa_dialog(event: MessageCreated):
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
        user_prompt = prompts.user_prompt_new_rec_tests.format(
            anketa=anketa_text
        )

        recs = await get_gpt_answer(
            system_prompt=prompts.system_prompt_new_rec_tests,
            user_prompt=user_prompt,
            bot=event
        )

        risks, recommendations_list, rec_text = ai_utils.extract_recs(recs)

        # ===== ЕСЛИ ЕСТЬ РЕКОМЕНДАЦИИ =====
        if recommendations_list:

            await event.message.answer(
                f"Проанализировав ваши ответы, я выявил некоторые риски:\n{risks}\n"
            )

            await asyncio.sleep(5)

            await event.message.answer(
                "На основе этого анализа я сформировал ПЕРСОНАЛЬНУЮ РЕКОМЕНДАЦИЮ.\n"
                f"Вам полезно пройти комплекс исследований:\n{rec_text}"
            )

            await asyncio.sleep(2)

            await event.message.answer(
                "Также вы можете выбрать любой из представленных комплексов услуг.\n"
                "Ознакомиться можно по ссылке:\n"
                f"https://telegra.ph/CHek-apy-po-laboratorii-OOO-CHelovek-02-06?ver={int(datetime.now().timestamp())}"
            )

            await asyncio.sleep(2)
            keyboard_builder = InlineKeyboardBuilder()
            keyboard_builder.row(CallbackButton(text = "Да", payload="dop_yes"),
                                CallbackButton(text = "Нет", payload="dop_no"))

            await event.message.answer(
                resources.by_dop_tests_or_not_text,
                attachments= [keyboard_builder.as_markup()]
            )

        # ===== ЕСЛИ РЕКОМЕНДАЦИЙ НЕТ =====
        else:
            await anamnez_db.append_answer(
                telegram_id=user_id,
                text=f"Терапевт сказал:{resources.is_has_complaint_text}"
            )

            await anamnez_db.set_dialog_state(
                user_id,
                resources.dialog_states_dict["is_has_complaint"]
            )

            await event.message.answer(
                resources.is_has_complaint_text
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

    # Получаем mode из состояния БД
    state = await anamnez_db.get_user_state(user_id)
    mode = state.get("mode")

    # Безопасность: проверка длины анкеты
    if len(answers) < 13:
        raise ValueError("Недостаточно ответов для сохранения анкеты")

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

        anketa = await anamnez_db.get_anketa(user_id=user_id)
        date = anketa.get("osmotr_date")

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

        await after_tests_main_menu(event)

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
    if state != "SELECTING_TESTS":
        return

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
                chat_id=event.from_user.id,
                text="Выберите хотя бы один анализ."
            )
            return

        chosen_names = [resources.TESTS[i] for i in selected]
        chosen_str = ", ".join(chosen_names)

        chat_id,user_id = event.get_ids()

        # получаем данные из БД (они постоянные)
        user_data = await anamnez_db.get_user(user_id=user_id)
        anketa = await anamnez_db.get_anketa(user_id=user_id)

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
            f"Планирует пройти дополнительные обследования.\n\n"
            f"Обследования: {chosen_str}"
        )

        await max_bot_chat_manager.send_to_chat(event, user_id, text_to_manager)

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

        await event.bot.send_message(
            chat_id=chat_id,
            text=resources.get_final_text_tests_with_price2(
                tests=text,
                price=price
            )
        )

        await asyncio.sleep(5)

        await after_tests_main_menu(event)

        await context_data.clear()

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