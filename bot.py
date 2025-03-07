

from telethon import TelegramClient, events
import asyncio
import shlex
import random

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID'))         # Required: Your Telegram API ID
API_HASH = os.getenv('API_HASH')          # Required: Your Telegram API Hash
SESSION_NAME = os.getenv('SESSION_NAME')  # Required: Your session name
ADMIN_ID = int(os.getenv('ADMIN_ID'))    # Required: Your Telegram User ID
DELAY_SECONDS = int(os.getenv('DELAY_SECONDS', '15'))  # Optional: Delay between messages

# Initialize client with proper session handling for Railway
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Error handler for connection issues
@client.on(events.Error)
async def error_handler(event):
    print(f"Connection error occurred: {event.text}")
    await asyncio.sleep(5)  # Wait before reconnecting

async def smart_broadcast(messages):
    sent = 0
    shuffled_messages = random.sample(messages, len(messages))
    
    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            try:
                # Get unique message for each group
                msg = shuffled_messages[sent % len(shuffled_messages)]
                await client.send_message(dialog.id, msg)
                sent += 1
                await asyncio.sleep(DELAY_SECONDS)
            except Exception as e:
                print(f"Failed in {dialog.name}: {str(e)}")
    return sent

@client.on(events.NewMessage(pattern='/broadcast', from_users=ADMIN_ID))
async def handler(event):
    try:
        # Properly parse quoted messages
        parts = shlex.split(event.raw_text)
        messages = parts[1:]  # Skip /broadcast command
    except:
        await event.reply("❌ Invalid format! Use: /broadcast \"Message 1\" \"Message 2\"")
        return

    if not messages:
        await event.reply("❌ No messages provided!")
        return

    status = await event.reply(f"🌀 Shuffling {len(messages)} messages...")
    count = await smart_broadcast(messages)
    await status.edit(f"✅ Broadcast complete!\nSent {count} messages")

print("PythonAnywhere Broadcast System Active!")
client.start()
client.run_until_disconnected()