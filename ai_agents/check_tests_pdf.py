import fitz  # это PyMuPDF

from ai_agents import open_ai_main
import json
from typing import List, Dict, Optional, Tuple
from ai_agents.prompts import system_prompt_check_tests_results, user_prompt_check_tests_results
import g_drive_funs

def pdf_to_text(path: str) -> str:
    doc = fitz.open(path)
    text = ""

    for page in doc:
        text += page.get_text()

    return text


def parse_analysis_json(raw_response: str) -> Tuple[str, Optional[List[Dict[str, str]]]]:
    """
    Возвращает:
    result: "complete" | "need_consult" | "error"
    dop_info: list или None
    """

    if not raw_response or not raw_response.strip():
        return "error", None

    # чистим markdown если вдруг пришёл ```json
    raw_response = raw_response.strip()
    if raw_response.startswith("```"):
        lines = raw_response.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_response = "\n".join(lines).strip()

    try:
        data = json.loads(raw_response)
    except Exception:
        return "error", None

    if not isinstance(data, dict):
        return "error", None

    result = data.get("result")

    if result == "complete":
        return "complete", None

    if result == "need_consult":
        dop_info = data.get("dop_info")

        if not isinstance(dop_info, list):
            return "error", None

        cleaned: List[Dict[str, str]] = []

        for item in dop_info:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip()
            value = str(item.get("value", "")).strip()
            norm = str(item.get("norm", "")).strip()

            if not name or not value or not norm:
                continue

            cleaned.append({
                "name": name,
                "value": value,
                "norm": norm
            })

        return "need_consult", cleaned if cleaned else None

    return "error", None


async def check_one_result(link:str, sex, age, bot):
    path_to_file = await g_drive_funs.download_google_drive_files(urls = link, output_dir="temp_downloads",timeout=60)

    text_from_pdf = pdf_to_text(path_to_file[0])
    user_prompt = user_prompt_check_tests_results.format(tests_result = text_from_pdf, sex =sex, age =age  )

    agent_answer = await open_ai_main.get_gpt_answer(system_prompt=system_prompt_check_tests_results, user_prompt=user_prompt, bot= bot)
    result, list_problems = parse_analysis_json(agent_answer)
    return result, list_problems

async def check_list_result(links:List[str], sex , age, bot = None):
    all_problem_list = []
    for link in links:
        result, list_problems = await check_one_result(link = link, bot = bot, age=age, sex= sex)
        all_problem_list.append(list_problems)
        if result == "need_consult":
            all_problem_list.append(list_problems)

    if all_problem_list:
        print(all_problem_list)
        return "need_consult", all_problem_list

    else:
        print("no problems")
        return "complete", None




# if __name__ == "__main__":
#     links = [
#         "https://drive.google.com/file/d/1t5bBP1MfcOkyFgGwcm0zPDlnBCoZ9WOV/view?usp=drivesdk",
#
#     ]
#
#     asyncio.run(check_list_result(links= links))

