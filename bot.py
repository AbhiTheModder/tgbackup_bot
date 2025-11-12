import asyncio
import logging
from configparser import ConfigParser

from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.tl.types import MessageService, PeerChannel, PeerChat

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

config = ConfigParser()
config.read("config.ini")

API_ID = int(config.get("Telegram", "api_id"))
API_HASH = config.get("Telegram", "api_hash")
BOT_TOKEN = config.get("Telegram", "bot_token")
CLONE = config.getboolean("Telegram", "clone")
BATCH_SIZE = config.getint("Telegram", "batch_size")

client = TelegramClient("backup_bot", API_ID, API_HASH)


@client.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    await event.respond(
        "Hello! Send me a message in this format:\n/forward chat_id start_id end_id"
    )


@client.on(events.NewMessage(pattern="/forward"))
async def forward_messages(event: Message):
    try:
        args = event.message.text.split()
        if len(args) != 4:
            await event.respond(
                "Please use the format: /forward chat_id start_id end_id"
            )
            return

        try:
            chat_id, start_id, end_id = map(int, args[1:4])
        except ValueError:
            await event.respond("Invalid chat_id, start_id, or end_id")
            return

        logging.debug(f"Chat ID: {chat_id}, Start ID: {start_id}, End ID: {end_id}")

        try:
            if chat_id < 0:
                peer = PeerChannel(chat_id)
            elif chat_id > 0:
                peer = PeerChat(int("-100" + str(chat_id)))
            else:
                await event.respond(
                    "[ERROR] Invalid chat ID: 0 is not a valid chat, group, or channel identifier."
                )
                return

            status_msg = await event.respond("Starting to forward messages...")

            message_ids = list(range(start_id, end_id + 1))
            total_messages = len(message_ids)
            logging.debug(f"Total messages to forward: {len(message_ids)}")

            messages_forwarded = 0

            is_group = event.is_group or event.is_channel
            delay = 3 if is_group else 1

            for i in range(0, len(message_ids), BATCH_SIZE):
                batch_ids = message_ids[i : i + BATCH_SIZE]
                # This is workaround for bots since they can't directly fetch whole chat history from a channel/group
                messages = await client.get_messages(peer, ids=batch_ids)
                logging.debug(f"Fetched {len(messages)} messages in this batch")
                logging.debug(f"Messages: {messages}")

                valid_messages = [
                    msg
                    for msg in messages
                    if msg is not None and not isinstance(msg, MessageService)
                ]

                if valid_messages:
                    batch_fwd_count = 0
                    for msg in valid_messages:
                        try:
                            await client.forward_messages(
                                entity=event.chat_id,
                                messages=msg,
                                from_peer=peer,
                                drop_author=CLONE,
                                silent=True,
                            )
                            batch_fwd_count += 1
                        except Exception as e:
                            logging.warning(f"Could not forward message {msg.id}: {e}")

                        await asyncio.sleep(delay)

                    messages_forwarded += batch_fwd_count
                    await status_msg.edit(
                        f"Forwarded {messages_forwarded} of {total_messages} messages..."
                    )

            await status_msg.edit(
                f"✅ Forwarding complete! Successfully forwarded {messages_forwarded} messages."
            )
            await status_msg.delete()

        except Exception as e:
            logging.error(f"Error forwarding messages: {str(e)}")
            pass

    except ValueError:
        await event.respond("Please provide valid numeric chat_id and message IDs")


def main():
    print("Starting bot...")
    client.start(bot_token=BOT_TOKEN)
    print("Bot is running...")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
