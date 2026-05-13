from dotenv import load_dotenv
import os
from maxapi import Dispatcher, Bot
load_dotenv()
TOKEN = os.environ.get("MAX_TOKEN")



bot = Bot(TOKEN)
dp = Dispatcher()
