import re
import os
import tempfile
from typing import Optional
import aiohttp
from docx import Document
from maxapi.enums.upload_type import UploadType
from maxapi.types import InputMedia

from db.after_tests.after_tests_db import get_user_sex
from db.anamnez.anamnez_db import get_anketa

GOOGLE_DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")

GOOGLE_DRIVE_FILE_ID_RE = re.compile(
    r"https?://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)"
)


def extract_google_doc_id(url: str) -> Optional[str]:
    """
    Возвращает Google Drive File ID из ссылки вида:
    https://drive.google.com/file/d/<ID>/view?...
    """
    m = GOOGLE_DRIVE_FILE_ID_RE.search(url or "")
    return m.group(1) if m else None


async def download_google_doc_as_docx(file_id: str, suffix: str = ".pdf") -> str:
    """
    Скачивает файл из Google Drive во временный файл.
    Возвращает путь к скачанному файлу.
    """

    # Прямая ссылка на скачивание файла
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    fd, tmp_path = tempfile.mkstemp(prefix="gdrive_", suffix=suffix)
    os.close(fd)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, allow_redirects=True) as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        f"Google Drive download failed: HTTP {resp.status}"
                    )

                data = await resp.read()

        with open(tmp_path, "wb") as f:
            f.write(data)

        return tmp_path

    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise



def extract_text_from_docx(docx_path: str) -> str:
    """
    Достаёт текст из .docx (параграфы -> строки).
    """
    doc = Document(docx_path)
    lines = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n".join(lines).strip()

def split_urls_from_cell(cell_value: str) -> list[str]:
    """
    В ячейке ссылки записаны построчно.
    Дополнительно чистим пробелы и пустые строки.
    """
    if not cell_value:
        return []
    lines = str(cell_value).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    urls = []
    for line in lines:
        u = line.strip()
        if u:
            urls.append(u)
    return urls


async def send_results_doc_and_text(event,
    doc_urls: str,
):
    chat_id, user_id = event.get_ids()

    urls = split_urls_from_cell(doc_urls)
    if not urls:
        await  event.bot.send_message(user_id= user_id, text="В ячейке нет ссылок на документы.")
        return

    await event.bot.send_message(user_id= user_id, text=f"Нашёл документов: {len(urls)}. Отправляю…")

    sent = 0
    failed = 0

    for idx, url in enumerate(urls, start=1):
        doc_id = extract_google_doc_id(url)
        if not doc_id:
            failed += 1
            await event.bot.send_message(
                user_id= user_id,
                text=f"[{idx}/{len(urls)}] Ссылка:\n{url}"
            )
            continue

        tmp_path = None
        try:
            tmp_path = await download_google_doc_as_docx(doc_id)

            await event.bot.send_message(
                user_id=user_id,
                text=f"✅ Результаты ({idx}/{len(urls)})",
                attachments=[InputMedia(path=tmp_path,
                                        type=UploadType.FILE)]
            )

            sent += 1

        except Exception as e:
            failed += 1
            await event.bot.send_message(
                user_id= user_id,
                text=f"❌ [{idx}/{len(urls)}] Не получилось скачать/прочитать документ:\n{url}\nПерейдите по ссылке выше и скачайте документ в ручном режиме."
            )

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

def build_anketa_text(anketa: dict, user_sex) -> str:
    return f"""
АНКЕТА ПОЛЬЗОВАТЕЛЯ

ID пользователя: {anketa.get("user_id")}
Организация / ИНН: {anketa.get("organization_or_inn")}
Дата осмотра: {anketa.get("osmotr_date")}
Пол: {user_sex}
Возраст: {anketa.get("age")}
Вес: {anketa.get("weight")}
Рост: {anketa.get("height")}
Курение: {anketa.get("smoking")}
Алкоголь: {anketa.get("alcohol")}
Физическая активность: {anketa.get("physical_activity")}
Гипертония: {anketa.get("hypertension")}
Потемнение в глазах: {anketa.get("darkening_of_the_eyes")}
Сахар: {anketa.get("sugar")}
Боль в суставах: {anketa.get("joint_pain")}
Хронические заболевания: {anketa.get("chronic_diseases")}
"""

async def create_anketa_txt(user_id: int) -> str | None:
    anketa = await get_anketa(user_id)
    user_sex = await get_user_sex(user_id)
    if not anketa:
        return None
    if user_sex is None or user_sex == "":
        user_sex = "Нет данных"
    anketa_text = build_anketa_text(anketa, user_sex)

    filename = f"anketa_{user_id}.txt"

    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(anketa_text)

    return file_path


async def delete_file(file_path: str) -> bool:
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Ошибка при удалении файла {file_path}: {e}")
        return False

