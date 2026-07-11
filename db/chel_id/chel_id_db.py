import aiosqlite
import asyncio
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

db_path = 'chel_id.db'


BASE_DIR = Path(__file__).resolve().parents[2]
CREDS_PATH = BASE_DIR / "docs" / "chelids-a1c86cf2007d.json"

# ==== Настройки Google API ====
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_NAME = "chel_id"  # Имя файла в Google Sheets


async def init_db():
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS chel_ids_sheet (
                chel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                max_id INTEGER UNIQUE NOT NULL
            )
        """)

    await sync_from_google_sheets_chel_id()



async def get_or_create_and_get_chel_id(max_id: int) -> int:
    async with aiosqlite.connect(db_path) as db:

        cursor = await db.execute(
            "SELECT chel_id FROM chel_ids_sheet WHERE max_id = ?",
            (max_id,)
        )
        row = await cursor.fetchone()

        if row:
            return row[0]

        cursor = await db.execute(
            "INSERT INTO chel_ids_sheet (max_id) VALUES (?)",
            (max_id,)
        )

        await db.commit()

        return cursor.lastrowid

async def get_chel_id(max_id: int) -> int | None:
    async with aiosqlite.connect(db_path) as db:

        cursor = await db.execute(
            "SELECT chel_id FROM chel_ids_sheet WHERE max_id = ?",
            (max_id,)
        )
        row = await cursor.fetchone()

        return row[0] if row else None

async def get_max_id(chel_id: int) -> int | None:
    async with aiosqlite.connect(db_path) as db:

        cursor = await db.execute(
            "SELECT max_id FROM chel_ids_sheet WHERE chel_id = ?",
            (chel_id,)
        )
        row = await cursor.fetchone()

        return row[0] if row else None

async def delete_user_id(max_id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:

        cursor = await db.execute(
            "DELETE FROM chel_ids_sheet WHERE max_id = ?",
            (max_id,)
        )

        await db.commit()

        return cursor.rowcount > 0

async def get_max_ids() -> set[int]:
    """
    Возвращает множество всех max_id из chel_ids_sheet.
    """
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("""
            SELECT max_id
            FROM chel_ids_sheet
        """)

        rows = await cursor.fetchall()
        await cursor.close()

    return {row[0] for row in rows}









def get_sheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME)
    return {
        "chel_ids_sheet": sheet.worksheet("chel_ids_sheet"),
    }
# ==== Загрузка данных из Google Sheets в SQLite ====
async def sync_from_google_sheets_chel_id():
    sheets = get_sheet()
    async with aiosqlite.connect(db_path) as db:
        # Очистка таблиц
        await db.execute("DELETE FROM chel_ids_sheet")

        # chel_ids_sheet
        rows = sheets["chel_ids_sheet"].get_all_values()[1:]
        for r in rows:
            chel_id, max_id = r
            await db.execute(
                "INSERT INTO chel_ids_sheet (chel_id, max_id) VALUES (?, ?)",
                (chel_id, max_id)
            )


        await db.commit()
        print("[✅] Данные из Google Sheets CHEL_ID загружены в SQLite")

async def sync_to_google_sheets_chel_id():
    sheets = get_sheet()
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT chel_id, max_id FROM chel_ids_sheet") as cur:
            rows = await cur.fetchall()

        sheets["chel_ids_sheet"].clear()
        sheets["chel_ids_sheet"].update("A1", [["chel_id", "max_id"]] + rows)
    print("[✅] Данные CHEL_ID выгружены в Google Sheets")

async def periodic_sync(interval: int = 4600):
    while True:
        await asyncio.sleep(interval)
        try:
            await sync_to_google_sheets_chel_id()
            print(f"Успешная синхронизация.")
        except Exception as e:
            print(f"Ошибка при синхронизации в Google Sheets: {e}")