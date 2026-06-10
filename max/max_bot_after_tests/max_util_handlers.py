from maxapi.types import MessageCreated
from pathlib import Path
from maxapi.enums.upload_type import UploadType
from maxapi.types import InputMediaBuffer
from maxapi.types.attachments import Attachments

import resources
from api.api_funs import create_yookassa_payment
from db.after_tests import after_tests_db as db
from db.anamnez import anamnez_db as anamnez_db
from max.max_bot_after_tests.max_after_tests_keyboards import tests_keyboards
from max.max_bot_after_tests.max_after_tests_keyboards.tests_keyboards import kb_yookassa
from pydantic import TypeAdapter

video_paths = [Path(__file__).parent.parent.parent / "images" / "video_1.mp4",
               Path(__file__).parent.parent.parent / "images" / "video_2.mp4",
               Path(__file__).parent.parent.parent / "images" / "video_3.mp4"
               ]

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

async def get_statistic_inn_by_date(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
            user_id,
            resources.dialog_states["get_stat_inn_by_date"]
    )

    await event.bot.send_message(
            chat_id=chat_id,
            text="Введите полную дату :\n\n\n Или нажмите кнопку для отмены",
            attachments=[tests_keyboards.kb_statistic_inn_close()]
        )

async def get_dop_tests_statistic(event: MessageCreated):
    chat_id, _ = event.get_ids()
    result = await anamnez_db.get_dop_tests_stats()
    print(result)
    await event.bot.send_message(
            chat_id=chat_id,
            text= result
        )

async def handle_send_post_with_bt (event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
        user_id,
        resources.dialog_states["send_post_with_bt"]
    )

    await event.bot.send_message(
        chat_id=chat_id,
        text= "Пришлите пост и он будет отправлен с кнопками! (Наш канал и Главное меню)",
    )

async def handle_send_post_without_bt(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    await db.set_neuro_dialog_states(
        user_id,
        resources.dialog_states["send_post_without_bt"]
    )

    await event.bot.send_message(
        chat_id=chat_id,
        text= "Пришлите пост и он будет с одной кнопкой! (Главное меню)",
    )

async def get_price(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    await event.bot.send_message(
        chat_id=chat_id,
        text=resources.text_fake_price,
        attachments= [tests_keyboards.kb_price()]
    )

async def make_pay_50(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    payment = await create_yookassa_payment(amount= 50, user_id=user_id, user_email= "test@gmail.com",description= f"Оплата за консультацию({user_id})")
    confirmation_url = payment["confirmation_url"]

    await event.bot.send_message(chat_id = chat_id,
                                 user_id=user_id,
                                 text= "Ссылка для оплаты сформирована.Нажмите на кнопку ниже для оплаты.\n\n\nЕсли ссылка не открывается, проверьте отключен ли у вас VPN (ВПН), и попробуйте нажать на кнопку снова.",
                                 attachments= [kb_yookassa(url= confirmation_url)])

async def get_manager_d(event: MessageCreated):
    chat_id, user_id = event.get_ids()

    lines = await anamnez_db.get_manager_users_with_dop_tests("manager_D")
    print(lines)
    await event.bot.send_message(
        chat_id=chat_id,
        text= f"Всего у manager_D - {len(lines)} заявок",
        attachments= [tests_keyboards.kb_price()]
    )

async def upload_video(event: MessageCreated, video_file_path, video_count):
    chat_id, user_id = event.get_ids()
    with open(video_file_path, "rb") as video_file:
        buffer = video_file.read()  # читаем весь файл в память
        media = InputMediaBuffer(buffer=buffer, filename= f"video_{video_count}", type=UploadType.VIDEO)

        res = await event.bot.send_message(
            chat_id = chat_id,
            text= f"video_{video_count}",
            attachments=[media]
            )
        # print(res)

        att = res.message.body.attachments[0] if res.message.body.attachments else None
        await anamnez_db.add_upload_token(upload_name= f"video_{video_count}", upload_token= att.model_dump_json())


async def upload_videos(event: MessageCreated):
    chat_id, user_id = event.get_ids()
    video_count = 1
    for path in video_paths:
        await upload_video(event, path, video_count)
        video_count += 1

    # att_json = await anamnez_db.get_upload_token(upload_name= str(video_paths[0]))
    # attachment_adapter = TypeAdapter(Attachments)
    # attachment = attachment_adapter.validate_json(
    #     att_json
    # )
    #
    # await event.bot.send_message(
    #     chat_id=chat_id,
    #     text= "Повтор",
    #     attachments=[attachment]
    # )

async def get_video_attachments_by_name(video_name):
    att_json = await anamnez_db.get_upload_token(upload_name= video_name)
    attachment_adapter = TypeAdapter(Attachments)
    attachment = attachment_adapter.validate_json(
        att_json
    )
    return attachment
