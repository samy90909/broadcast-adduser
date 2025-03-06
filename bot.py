

from telethon import TelegramClient, events
import asyncio
import shlex
import random

# Configuration
API_ID = 29563112  # Your API ID
API_HASH = 'd15f1b48e5746765542748e72146c4fe'   # Your API hash
SESSION_NAME = 'smart_broadcaster' # Your session name
ADMIN_ID = 8135139895 # Your Telegram ID
DELAY_SECONDS = 15 # Delay in seconds between messages 
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

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