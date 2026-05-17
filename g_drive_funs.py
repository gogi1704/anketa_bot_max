import asyncio
import re
import uuid
from pathlib import Path
from typing import List, Union, Optional
from urllib.parse import urlparse, parse_qs, unquote
import requests

from api.api_funs import pay_completed, pay_canceled, complete_send_notify
from db.anamnez import anamnez_db
from db.anamnez.anamnez_db import sync_and_get_from_google_sheets_payments


class GoogleDriveDownloadError(Exception):
    pass


def extract_google_drive_file_id(url: str) -> str:
    """
    Поддерживает ссылки вида:
    - https://drive.google.com/file/d/FILE_ID/view?usp=...
    - https://drive.google.com/open?id=FILE_ID
    - https://drive.google.com/uc?id=FILE_ID
    """
    url = url.strip()

    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    if "id" in query_params and query_params["id"]:
        return query_params["id"][0]

    raise ValueError(f"Не удалось извлечь file_id из ссылки: {url}")


def get_confirm_token_from_response(response: requests.Response) -> Optional[str]:
    """
    Иногда Google Drive просит confirm token.
    """
    for key, value in response.cookies.items():
        if key.startswith("download_warning"):
            return value

    try:
        match = re.search(r"confirm=([0-9A-Za-z_]+)", response.text)
        if match:
            return match.group(1)
    except Exception:
        pass

    return None


def resolve_filename_from_response(response: requests.Response, default_name: str) -> str:
    """
    Пытается вытащить имя файла из Content-Disposition.
    """
    content_disposition = response.headers.get("Content-Disposition", "")

    match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
    if match:
        return unquote(match.group(1))

    match = re.search(r'filename="([^"]+)"', content_disposition)
    if match:
        return match.group(1)

    return default_name


def ensure_pdf_extension(filename: str, fallback_stem: str) -> str:
    filename = filename.strip()
    if not filename:
        filename = f"{fallback_stem}.pdf"

    suffix = Path(filename).suffix.lower()
    if suffix != ".pdf":
        filename = f"{Path(filename).stem or fallback_stem}.pdf"

    return filename


def download_google_drive_file_sync(
    url: str,
    output_dir: Union[str, Path] = "temp_downloads",
    timeout: int = 60,
    session: Optional[requests.Session] = None,
) -> str:
    """
    Синхронно скачивает один файл с Google Drive и возвращает путь к нему.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_id = extract_google_drive_file_id(url)
    download_url = "https://drive.google.com/uc?export=download"

    own_session = session is None
    sess = session or requests.Session()

    try:
        # Первый запрос
        response = sess.get(
            download_url,
            params={"id": file_id},
            stream=True,
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        content_disposition = response.headers.get("Content-Disposition", "")

        # Если файл отдался сразу
        if "attachment" in content_disposition.lower() or "application/pdf" in content_type:
            filename = resolve_filename_from_response(response, f"{file_id}.pdf")
            filename = ensure_pdf_extension(filename, file_id)

            unique_name = f"{Path(filename).stem}_{uuid.uuid4().hex[:8]}.pdf"
            file_path = output_dir / unique_name

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)

            response.close()
            return str(file_path)

        # Ищем confirm token
        confirm_token = get_confirm_token_from_response(response)
        response.close()

        params = {"id": file_id}
        if confirm_token:
            params["confirm"] = confirm_token

        response = sess.get(
            download_url,
            params=params,
            stream=True,
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        content_disposition = response.headers.get("Content-Disposition", "")

        if "text/html" in content_type and "attachment" not in content_disposition.lower():
            sample = ""
            try:
                sample = response.text[:500]
            except Exception:
                pass
            response.close()
            raise GoogleDriveDownloadError(
                "Не удалось скачать файл. Вероятно, ссылка не публичная "
                "или Google Drive вернул HTML вместо файла.\n"
                f"URL: {url}\n"
                f"FILE_ID: {file_id}\n"
                f"Ответ: {sample}"
            )

        filename = resolve_filename_from_response(response, f"{file_id}.pdf")
        filename = ensure_pdf_extension(filename, file_id)

        unique_name = f"{Path(filename).stem}_{uuid.uuid4().hex[:8]}.pdf"
        file_path = output_dir / unique_name

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

        response.close()
        return str(file_path)

    except requests.RequestException as e:
        raise GoogleDriveDownloadError(
            f"Ошибка скачивания файла с Google Drive: {url}\n{e}"
        ) from e
    finally:
        if own_session:
            sess.close()


def download_google_drive_files_sync(
    urls: Union[str, List[str]],
    output_dir: Union[str, Path] = "temp_downloads",
    timeout: int = 60,
) -> List[str]:
    """
    Синхронно скачивает одну или несколько ссылок.
    Возвращает список путей к файлам.
    """
    if isinstance(urls, str):
        urls = [urls]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded_paths: List[str] = []

    with requests.Session() as session:
        for url in urls:
            path = download_google_drive_file_sync(
                url=url,
                output_dir=output_dir,
                timeout=timeout,
                session=session,
            )
            downloaded_paths.append(path)

    return downloaded_paths


def delete_files_by_paths_sync(paths: Union[str, List[str]]) -> List[str]:
    """
    Синхронно удаляет файл или список файлов.
    Возвращает список реально удалённых путей.
    """
    if isinstance(paths, str):
        paths = [paths]

    deleted: List[str] = []

    for path in paths:
        try:
            p = Path(path)
            if p.exists() and p.is_file():
                p.unlink()
                deleted.append(str(p))
        except Exception:
            pass

    return deleted


def delete_directory_if_exists_sync(dir_path: Union[str, Path]) -> bool:
    """
    Синхронно удаляет целиком папку со всем содержимым.
    """
    dir_path = Path(dir_path)

    if not dir_path.exists() or not dir_path.is_dir():
        return False

    try:
        for child in dir_path.iterdir():
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                import shutil
                shutil.rmtree(child)

        dir_path.rmdir()
        return True
    except Exception:
        return False


# =========================
# ASYNC WRAPPERS
# =========================

async def download_google_drive_file(
    url: str,
    output_dir: Union[str, Path] = "temp_downloads",
    timeout: int = 60,
) -> str:
    """
    Async-обёртка над sync-скачиванием одного файла.
    """
    return await asyncio.to_thread(
        download_google_drive_file_sync,
        url,
        output_dir,
        timeout,
    )


async def download_google_drive_files(
    urls: Union[str, List[str]],
    output_dir: Union[str, Path] = "temp_downloads",
    timeout: int = 60,
) -> List[str]:
    """
    Async-обёртка над sync-скачиванием списка файлов.
    Выполняется в отдельном потоке, не блокируя event loop.
    """
    return await asyncio.to_thread(
        download_google_drive_files_sync,
        urls,
        output_dir,
        timeout,
    )


async def delete_files_by_paths(paths: Union[str, List[str]]) -> List[str]:
    """
    Async-обёртка над sync-удалением файлов.
    """
    return await asyncio.to_thread(delete_files_by_paths_sync, paths)


async def delete_directory_if_exists(dir_path: Union[str, Path]) -> bool:
    """
    Async-обёртка над sync-удалением директории.
    """
    return await asyncio.to_thread(delete_directory_if_exists_sync, dir_path)


# =========================
# OPTIONAL HELPERS
# =========================

def normalize_links(links: Union[str, List[str], None]) -> List[str]:
    if links is None:
        return []

    if isinstance(links, str):
        links = [links]

    return [x.strip() for x in links if x and x.strip()]


async def download_and_return_paths(
    links: Union[str, List[str]],
    output_dir: Union[str, Path] = "temp_downloads",
    timeout: int = 60,
) -> List[str]:
    """
    Удобный alias-метод.
    """
    links = normalize_links(links)
    if not links:
        return []

    return await download_google_drive_files(
        urls=links,
        output_dir=output_dir,
        timeout=timeout,
    )



async def payment_notifications_worker():
    while True:
        print("NOTIFY")
        sheets = await sync_and_get_from_google_sheets_payments()
        payments_sheet = sheets["payments"]
        rows = payments_sheet.get_all_records()

        try:
            for index, row in enumerate(rows, start=2):
                status = str(row.get("status", "")).strip().lower()
                notify_send = str(row.get("notify_send", "")).strip().lower()
                user_id = row.get("user_id")
                payment_id = str(row.get("payment_id")).strip().lower()

                # уже обработано
                if notify_send in ["1", "true"]:
                    continue

                # успешная оплата
                if status == "succeeded":

                    await pay_completed(int(user_id), payment_id)
                    await complete_send_notify(payment_id)
                    await anamnez_db.set_payment_notified(payment_id)

                    print(f"SUCCESS notify sent: {user_id}")

                # отмененная оплата
                elif status == "canceled":

                    await pay_canceled(int(user_id), payment_id)
                    await complete_send_notify(payment_id)
                    await anamnez_db.set_payment_notified(payment_id)

                    print(f"CANCELED notify sent: {user_id}")

        except Exception as e:
            print(f"payment worker error: {e}")

        await asyncio.sleep(120)