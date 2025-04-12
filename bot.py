from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, MessageService
import logging
from configparser import ConfigParser
import asyncio  # For adding delays between batches

# Configure logging
logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

# Load configuration
config = ConfigParser()
config.read("config.ini")

API_ID = config.get("Telegram", "api_id")
API_HASH = config.get("Telegram", "api_hash")
BOT_TOKEN = config.get("Telegram", "bot_token")
CLONE = config.getboolean("Telegram", "clone")
BATCH_SIZE = config.getint("Telegram", "batch_size")

# Initialize Telegram client
client = TelegramClient("backup_bot", API_ID, API_HASH)

# Helper function to determine peer type
def resolve_peer(chat_id: int):
    if chat_id < 0:
        return PeerChannel(int(str(chat_id)[4:])) if str(chat_id).startswith("-100") else PeerChat(-chat_id)
    return PeerUser(chat_id)

# Start command handler
@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond(
        "Hello! Send me a message in this format:\n/forward chat_id start_id end_id"
    )

# Forward messages command handler
@client.on(events.NewMessage(pattern="/forward"))
async def forward_messages(event):
    args = event.message.text.split()
    if len(args) != 4 or not all(arg.isdigit() for arg in args[1:]):
        await event.respond("Please use the format: /forward chat_id start_id end_id")
        return

    chat_id, start_id, end_id = map(int, args[1:])
    peer = resolve_peer(chat_id)

    try:
        status_msg = await event.respond("Starting to forward messages...")
        message_ids = list(range(start_id, end_id + 1))
        total_messages = len(message_ids)
        messages_forwarded = 0

        for i in range(0, len(message_ids), BATCH_SIZE):
            batch_ids = message_ids[i : i + BATCH_SIZE]
            messages = await client.get_messages(peer, ids=batch_ids)

            # Filter valid messages
            valid_messages = [
                msg for msg in messages if msg is not None and not isinstance(msg, MessageService)
            ]

            if valid_messages:
                await client.forward_messages(
                    entity=event.chat_id,
                    messages=valid_messages,
                    from_peer=peer,
                    drop_author=CLONE,
                    silent=True,
                )
                messages_forwarded += len(valid_messages)
                await status_msg.edit(
                    f"Forwarded {messages_forwarded} of {total_messages} messages..."
                )

            # Add a small delay to avoid API rate limits
            await asyncio.sleep(0.5)

        await status_msg.edit(
            f"✅ Forwarding complete! Successfully forwarded {messages_forwarded} messages."
        )

    except Exception as e:
        logging.error(f"Error forwarding messages: {str(e)}")
        await event.respond(f"An error occurred: {str(e)}")

# Main function
def main():
    print("Starting bot...")
    client.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    client.run_until_disconnected()

if __name__ == "__main__":
    main()