

from telethon import TelegramClient, events
from telethon.sessions import StringSession
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
SESSION_STRING = os.getenv('SESSION_STRING')  # Required: Your session string
ADMIN_ID = int(os.getenv('ADMIN_ID'))    # Required: Your Telegram User ID
DELAY_SECONDS = int(os.getenv('DELAY_SECONDS', '15'))  # Optional: Delay between messages

# Initialize client with session string
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# Connection handling


async def main():
    print("Starting Telegram Bot...")
    try:
        await client.start()
        print("\nBot is now running!")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"Error starting bot: {str(e)}")
        raise

async def smart_broadcast(messages):
    sent = 0
    failed = 0
    shuffled_messages = random.sample(messages, len(messages))
    
    async for dialog in client.iter_dialogs():
        if dialog.is_group:
            try:
                # Get unique message for each group
                msg = shuffled_messages[sent % len(shuffled_messages)]
                await client.send_message(dialog.id, msg)
                sent += 1
                print(f"Successfully sent message to {dialog.name}")
                await asyncio.sleep(DELAY_SECONDS)
            except Exception as e:
                failed += 1
                print(f"Failed in {dialog.name}: {str(e)}")
    return sent, failed

@client.on(events.NewMessage(pattern='/broadcast', from_users=ADMIN_ID))
async def handler(event):
    try:
        # Properly parse quoted messages
        parts = shlex.split(event.raw_text)
        messages = parts[1:]  # Skip /broadcast command
    except Exception as e:
        await event.reply(f"❌ Invalid format! Error: {str(e)}\nUse: /broadcast \"Message 1\" \"Message 2\"")
        return

    if not messages:
        await event.reply("❌ No messages provided!")
        return

    status = await event.reply(f"🌀 Starting broadcast with {len(messages)} messages...")
    sent, failed = await smart_broadcast(messages)
    await status.edit(f"✅ Broadcast complete!\n✓ Successfully sent: {sent}\n✗ Failed: {failed}")

if __name__ == '__main__':
    print("Telegram Broadcast Bot Starting...")
    client.loop.run_until_complete(main())