from telethon import TelegramClient, events, types
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, ChatAdminRequiredError, ChannelPrivateError
import asyncio
import os
import random
import shlex
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration with validation
try:
    API_ID = int(os.environ['API_ID'])
    API_HASH = os.environ['API_HASH']
    SESSION_STRING = os.environ['SESSION_STRING']
    ADMIN_ID = int(os.environ['ADMIN_ID'])
    BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '30'))
    BASE_DELAY = int(os.environ.get('BASE_DELAY', '60'))
    DAILY_LIMIT = int(os.environ.get('DAILY_LIMIT', '150'))
    FLOOD_WAIT_MULTIPLIER = float(os.environ.get('FLOOD_WAIT_MULTIPLIER', '2.0'))
    BROADCAST_DELAY = int(os.environ.get('BROADCAST_DELAY', '15'))
except (KeyError, ValueError) as e:
    logger.error(f"Configuration error: {str(e)}")
    exit(1)

# Global state
active_migrations = {}
scheduled_broadcasts = {}
daily_counter_file = "daily_counter.txt"
current_delay = BASE_DELAY

# Initialize client
client = TelegramClient(
    StringSession(SESSION_STRING),
    API_ID,
    API_HASH,
    connection_retries=5,
    retry_delay=10,
    auto_reconnect=True
)

# --------------------- File Handling Functions ---------------------
def initialize_counter_file():
    if not os.path.exists(daily_counter_file):
        with open(daily_counter_file, 'w') as f:
            f.write(f"{datetime.now().isoformat()} 0")
        logger.info("Created new daily counter file")

def get_daily_counter():
    try:
        with open(daily_counter_file, "r") as f:
            last_date, count = f.read().split()
            if datetime.now().date() == datetime.fromisoformat(last_date).date():
                return int(count)
        return 0
    except FileNotFoundError:
        initialize_counter_file()
        return 0
    except Exception as e:
        logger.error(f"Counter read error: {str(e)}")
        return 0

def update_daily_counter(count):
    try:
        with open(daily_counter_file, "w") as f:
            f.write(f"{datetime.now().isoformat()} {count}")
    except Exception as e:
        logger.error(f"Counter update error: {str(e)}")

# --------------------- Migration Functions ---------------------
async def safe_add_members(source_group, target_group):
    global current_delay
    daily_count = get_daily_counter()
    
    try:
        source = await client.get_entity(source_group.strip('@'))
        target = await client.get_entity(target_group.strip('@'))
        
        participants = await client.get_participants(source, aggressive=False)
        participants = [u for u in participants if not u.bot]
        
        total_added = 0
        batch_number = 1
        
        while participants and daily_count < DAILY_LIMIT:
            batch = participants[:BATCH_SIZE]
            participants = participants[BATCH_SIZE:]
            
            status_message = (
                f"⚙️ Processing batch {batch_number}\n"
                f"• Remaining: {len(participants)}\n"
                f"• Daily added: {daily_count}/{DAILY_LIMIT}"
            )
            await client.send_message(ADMIN_ID, status_message)
            
            added_in_batch = 0
            for user in batch:
                if user.deleted or user.is_self:
                    continue
                
                try:
                    await client(InviteToChannelRequest(target, [user]))
                    added_in_batch += 1
                    daily_count += 1
                    update_daily_counter(daily_count)
                    
                    delay = current_delay + random.randint(5, 15)
                    logger.info(f"Added {user.id} | Delay: {delay}s")
                    await asyncio.sleep(delay)
                    
                except FloodWaitError as e:
                    logger.warning(f"Flood wait {e.seconds}s")
                    current_delay = max(current_delay * FLOOD_WAIT_MULTIPLIER, e.seconds)
                    await asyncio.sleep(e.seconds)
                    continue
                except UserPrivacyRestrictedError:
                    logger.info(f"Privacy restricted: {user.id}")
                except Exception as e:
                    logger.error(f"Error adding {user.id}: {str(e)}")
                
                if daily_count >= DAILY_LIMIT:
                    await client.send_message(ADMIN_ID, f"⚠️ Daily limit reached: {DAILY_LIMIT}")
                    return
                    
            total_added += added_in_batch
            batch_number += 1
            
            if participants:
                inter_batch_delay = current_delay * BATCH_SIZE
                logger.info(f"Batch complete. Waiting {inter_batch_delay//60} minutes")
                await asyncio.sleep(inter_batch_delay)
                
        return total_added, len(participants), None
        
    except Exception as e:
        logger.error(f"Migration error: {str(e)}")
        return 0, 0, f"❌ Critical error: {str(e)}"

# --------------------- Broadcast Functions ---------------------
async def smart_broadcast(messages):
    sent = 0
    failed = 0
    shuffled = random.sample(messages, len(messages))
    
    async for dialog in client.iter_dialogs():
        if dialog.is_group and sent < 50:
            try:
                msg = shuffled[sent % len(shuffled)]
                await client.send_message(dialog.id, msg)
                sent += 1
                await asyncio.sleep(BROADCAST_DELAY + random.randint(0, 10))
            except Exception as e:
                failed += 1
                logger.error(f"Broadcast failed in {dialog.name}: {str(e)}")
                await asyncio.sleep(30)
                
    return sent, failed

# --------------------- Scheduled Broadcasts ---------------------
async def broadcast_scheduler(job_id, times, interval_hours, message):
    start_time = datetime.now()
    remaining = times
    
    try:
        while remaining > 0 and (datetime.now() - start_time) < timedelta(hours=24):
            try:
                sent, failed = await smart_broadcast([message])
                await client.send_message(
                    ADMIN_ID,
                    f"📤 Scheduled broadcast ({times - remaining + 1}/{times})\n"
                    f"✓ Sent: {sent}\n✗ Failed: {failed}"
                )
                remaining -= 1
                if remaining > 0:
                    await asyncio.sleep(interval_hours * 3600)
            except Exception as e:
                logger.error(f"Scheduled broadcast error: {str(e)}")
                break
    finally:
        scheduled_broadcasts.pop(job_id, None)

# --------------------- Command Handlers ---------------------
@client.on(events.NewMessage(pattern='/schedule_broadcast', from_users=ADMIN_ID))
async def schedule_handler(event):
    try:
        parts = shlex.split(event.raw_text)
        if len(parts) < 4:
            await event.reply("❌ Usage: /schedule_broadcast <times> <interval_hours> <message>")
            return

        try:
            times = int(parts[1])
            interval = int(parts[2])
            message = " ".join(parts[3:])
        except ValueError:
            await event.reply("❌ Invalid parameters. Usage: /schedule_broadcast 10 2 'Your message'")
            return

        job_id = f"broadcast_{datetime.now().timestamp()}"
        task = asyncio.create_task(broadcast_scheduler(job_id, times, interval, message))
        scheduled_broadcasts[job_id] = task
        
        await event.reply(
            f"✅ Scheduled {times} broadcasts\n"
            f"⏰ Interval: {interval} hours\n"
            f"⏳ First broadcast starting now..."
        )

    except Exception as e:
        await event.reply(f"❌ Schedule error: {str(e)}")

@client.on(events.NewMessage(pattern='/stop_manual', from_users=ADMIN_ID))
async def stop_manual_handler(event):
    stopped = 0
    for job_id, task in list(scheduled_broadcasts.items()):
        task.cancel()
        stopped += 1
    scheduled_broadcasts.clear()
    
    if stopped:
        await event.reply(f"🛑 Stopped {stopped} scheduled broadcasts")
    else:
        await event.reply("ℹ️ No scheduled broadcasts running")

@client.on(events.NewMessage(pattern='/add_users', from_users=ADMIN_ID))
async def migration_handler(event):
    try:
        args = event.raw_text.split()[1:]
        if len(args) != 2:
            await event.reply("❌ Usage: /add_users [source] [target]")
            return
            
        migration_id = f"{datetime.now().timestamp()}"
        if len(active_migrations) >= 3:
            await event.reply("⚠️ Maximum 3 concurrent migrations allowed")
            return
            
        status = await event.reply("🚀 Starting smart migration...")
        task = asyncio.create_task(safe_add_members(args[0], args[1]))
        active_migrations[migration_id] = task
        
        try:
            await task
        finally:
            del active_migrations[migration_id]
            
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        await event.reply(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern='/broadcast', from_users=ADMIN_ID))
async def broadcast_handler(event):
    try:
        parts = shlex.split(event.raw_text)
        if len(parts) < 2:
            await event.reply("❌ Usage: /broadcast message")
            return

        messages = parts[1:]
        status = await event.reply("🌀 Starting safe broadcast...")
        sent, failed = await smart_broadcast(messages)
        await status.edit(f"✅ Broadcast complete!\n✓ Sent: {sent}\n✗ Failed: {failed}")
        
    except Exception as e:
        await event.reply(f"❌ Broadcast error: {str(e)}")

@client.on(events.NewMessage(pattern='/stop', from_users=ADMIN_ID))
async def stop_handler(event):
    stopped = []
    
    if active_migrations:
        for task in active_migrations.values():
            task.cancel()
        active_migrations.clear()
        stopped.append("migrations")
        
    if scheduled_broadcasts:
        for task in scheduled_broadcasts.values():
            task.cancel()
        scheduled_broadcasts.clear()
        stopped.append("broadcasts")
        
    if stopped:
        await event.reply(f"🛑 Stopped: {', '.join(stopped)}")
    else:
        await event.reply("ℹ️ No active operations to stop")

@client.on(events.NewMessage(pattern='/status', from_users=ADMIN_ID))
async def status_handler(event):
    daily_count = get_daily_counter()
    status_msg = [
        f"📊 System Status",
        f"• Daily added: {daily_count}/{DAILY_LIMIT}",
        f"• Active migrations: {len(active_migrations)}",
        f"• Scheduled broadcasts: {len(scheduled_broadcasts)}",
        f"• Current delay: {current_delay}s",
        f"• Next reset: {(datetime.now() + timedelta(hours=24 - datetime.now().hour)).strftime('%Y-%m-%d %H:%M')}"
    ]
    
    if scheduled_broadcasts:
        status_msg.append("\n📡 Active Broadcasts:")
        for job_id in scheduled_broadcasts:
            status_msg.append(f"- {job_id.split('_')[-1][:6]}...")
    
    await event.reply("\n".join(status_msg))

# --------------------- Main Execution ---------------------
async def main():
    await client.start()
    logger.info("Multi-Function Bot started successfully")
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        initialize_counter_file()
        file_date = datetime.fromtimestamp(os.path.getmtime(daily_counter_file)).date()
        if datetime.now().date() != file_date:
            update_daily_counter(0)
            
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")