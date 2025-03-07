

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

# Initialize client with proper session handling
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Connection handling
async def main():
    print("Starting Telegram Bot...")
    print("\nFirst time setup:")
    print("1. You'll be prompted for your phone number")
    print("2. Telegram will send you a code - enter it when prompted")
    print("3. If you have two-factor authentication enabled, you'll need to enter your password")
    
    await client.start()
    print("\nBot is now running!")
    await client.run_until_disconnected()

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

if __name__ == '__main__':
    print("Telegram Broadcast Bot Starting...")
    client.loop.run_until_complete(main())