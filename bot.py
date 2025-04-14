from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
import asyncio
import shlex
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
SESSION_STRING = os.getenv('SESSION_STRING')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
DELAY_SECONDS = int(os.getenv('DELAY_SECONDS', '15'))
MIGRATION_DELAY = int(os.getenv('MIGRATION_DELAY', '30'))

# Global state for migrations
active_migrations = {}

# Initialize client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

async def safe_add_members(source_group, target_group, max_members=50):
    """Safely migrate members with rate limiting"""
    try:
        source = await client.get_entity(source_group)
        target = await client.get_entity(target_group)
        
        participants = await client.get_participants(source, limit=max_members)
        added_count = 0
        
        for user in participants:
            if user.bot or user.is_self or user.deleted:
                continue
                
            try:
                await client(InviteToChannelRequest(target, [user]))
                added_count += 1
                await asyncio.sleep(MIGRATION_DELAY + random.randint(-5, 5))
            except Exception as e:
                if 'FloodWaitError' in str(e):
                    wait = int(str(e).split()[-2])
                    print(f"Flood wait detected: Sleeping {wait} seconds")
                    await asyncio.sleep(wait)
                elif 'USER_PRIVACY_RESTRICTED' not in str(e):
                    print(f"Error adding {user.id}: {str(e)}")
                    
        return added_count, len(participants)
    
    except Exception as e:
        print(f"Migration error: {str(e)}")
        return 0, 0

@client.on(events.NewMessage(pattern='/broadcast', from_users=ADMIN_ID))
async def broadcast_handler(event):
    """Enhanced broadcast command with safety checks"""
    try:
        parts = shlex.split(event.raw_text)
        messages = parts[1:]
        
        if not messages:
            await event.reply("❌ No messages provided!")
            return

        status = await event.reply("🌀 Starting safe broadcast...")
        sent, failed = await smart_broadcast(messages)
        await status.edit(f"✅ Broadcast complete!\n✓ Sent: {sent}\n✗ Failed: {failed}")
        
    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern='/add_members', from_users=ADMIN_ID))
async def migration_handler(event):
    """Safe member migration command"""
    try:
        args = event.raw_text.split()[1:]
        if len(args) != 2:
            await event.reply("❌ Usage: /add_members [source] [target]")
            return
            
        if event.chat_id in active_migrations:
            await event.reply("⚠️ Migration already in progress!")
            return
            
        active_migrations[event.chat_id] = True
        status = await event.reply("🚦 Starting SAFE member migration...")
        
        added, total = await safe_add_members(args[0], args[1])
        del active_migrations[event.chat_id]
        
        await status.edit(f"✅ Migration complete!\nAdded {added}/{total} members")
        
    except Exception as e:
        await event.reply(f"❌ Migration failed: {str(e)}")
        del active_migrations[event.chat_id]

@client.on(events.NewMessage(pattern='/stop', from_users=ADMIN_ID))
async def stop_handler(event):
    """Emergency stop command"""
    if event.chat_id in active_migrations:
        del active_migrations[event.chat_id]
        await event.reply("🛑 Migration stopped!")
    else:
        await event.reply("⚠️ No active operations to stop")

async def smart_broadcast(messages):
    """Broadcast with enhanced safety features"""
    sent = 0
    failed = 0
    shuffled = random.sample(messages, len(messages))
    
    async for dialog in client.iter_dialogs():
        if dialog.is_group and sent < 50:  # Daily limit safety
            try:
                msg = shuffled[sent % len(shuffled)]
                await client.send_message(dialog.id, msg)
                sent += 1
                await asyncio.sleep(DELAY_SECONDS + random.randint(0, 10))
            except Exception as e:
                failed += 1
                print(f"Failed in {dialog.name}: {str(e)}")
                await asyncio.sleep(30)  # Longer wait on errors
                
    return sent, failed

if __name__ == '__main__':
    print("Starting Enhanced Telegram Bot...")
    client.start()
    client.run_until_disconnected()

# from telethon import TelegramClient, events
# from telethon.sessions import StringSession
# import asyncio
# import shlex
# import random

# import os
# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# # Configuration
# API_ID = int(os.getenv('API_ID'))         # Required: Your Telegram API ID
# API_HASH = os.getenv('API_HASH')          # Required: Your Telegram API Hash
# SESSION_STRING = os.getenv('SESSION_STRING')  # Required: Your session string
# ADMIN_ID = int(os.getenv('ADMIN_ID'))    # Required: Your Telegram User ID
# DELAY_SECONDS = int(os.getenv('DELAY_SECONDS', '15'))  # Optional: Delay between messages

# # Initialize client with session string
# client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# # Connection handling


# async def main():
#     print("Starting Telegram Bot...")
#     try:
#         await client.connect()
#         if not await client.is_user_authorized():
#             print("Error: Session string is invalid or expired. Please generate a new one.")
#             return
#         print("\nBot is now running!")
#         await client.run_until_disconnected()
#     except Exception as e:
#         print(f"Error starting bot: {str(e)}")
#         raise

# async def smart_broadcast(messages):
#     sent = 0
#     failed = 0
#     shuffled_messages = random.sample(messages, len(messages))
    
#     async for dialog in client.iter_dialogs():
#         if dialog.is_group:
#             try:
#                 # Get unique message for each group
#                 msg = shuffled_messages[sent % len(shuffled_messages)]
#                 await client.send_message(dialog.id, msg)
#                 sent += 1
#                 print(f"Successfully sent message to {dialog.name}")
#                 await asyncio.sleep(DELAY_SECONDS)
#             except Exception as e:
#                 failed += 1
#                 print(f"Failed in {dialog.name}: {str(e)}")
#     return sent, failed

# @client.on(events.NewMessage(pattern='/broadcast', from_users=ADMIN_ID))
# async def handler(event):
#     try:
#         # Properly parse quoted messages
#         parts = shlex.split(event.raw_text)
#         messages = parts[1:]  # Skip /broadcast command
#     except Exception as e:
#         await event.reply(f"❌ Invalid format! Error: {str(e)}\nUse: /broadcast \"Message 1\" \"Message 2\"")
#         return

#     if not messages:
#         await event.reply("❌ No messages provided!")
#         return

#     status = await event.reply(f"🌀 Starting broadcast with {len(messages)} messages...")
#     sent, failed = await smart_broadcast(messages)
#     await status.edit(f"✅ Broadcast complete!\n✓ Successfully sent: {sent}\n✗ Failed: {failed}")

# if __name__ == '__main__':
#     print("Telegram Broadcast Bot Starting...")
#     client.loop.run_until_complete(main())

