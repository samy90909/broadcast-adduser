from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("Telegram Session String Generator")
print("-" * 30)

API_ID = input("Enter your API ID: ")
API_HASH = input("Enter your API HASH: ")

with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    session_string = client.session.save()
    print("\nYour session string has been generated:\n")
    print(session_string)
    print("\nPlease save this string securely and add it to your .env file.")