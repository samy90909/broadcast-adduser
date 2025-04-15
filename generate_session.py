from telethon.sync import TelegramClient
from telethon.sessions import StringSession

API_ID = 25344192
API_HASH = "ad3f44ae364bdb8bfc04b1454d77aef4"

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("SESSION_STRING:", client.session.save())