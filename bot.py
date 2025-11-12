import asyncio
import logging
import signal
from configparser import ConfigParser

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import Message

STOP_EVENT = asyncio.Event()
logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
signal.signal(signal.SIGINT, lambda _, __: STOP_EVENT.set())

config = ConfigParser()
config.read("config.ini")

API_ID = int(config.get("Telegram", "api_id"))
API_HASH = config.get("Telegram", "api_hash")
BOT_TOKEN = config.get("Telegram", "bot_token")
CLONE = config.getboolean("Telegram", "clone")
BATCH_SIZE = config.getint("Telegram", "batch_size")
WITH_FORUM = config.getboolean("Telegram", "with_forum")

client = Client("backup_bot", API_ID, API_HASH, bot_token=BOT_TOKEN)


@client.on_message(filters.command("start"))
async def start_handler(_: Client, message: Message):
    await message.reply(
        "Hello! Send me a message in this format:\n/forward chat_id start_id end_id"
    )


@client.on_message(filters.command("forward"))
async def forward_messages(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) != 4:
            await message.reply(
                "Please use the format: /forward chat_id start_id end_id"
            )
            return

        try:
            chat_id, start_id, end_id = map(int, args[1:4])
        except ValueError:
            await message.reply("Invalid chat_id, start_id, or end_id")
            return

        logging.debug(f"Chat ID: {chat_id}, Start ID: {start_id}, End ID: {end_id}")

        try:
            if str(chat_id).startswith("-100"):
                peer = int(chat_id)
            else:
                peer = int("-100" + str(chat_id))
            if WITH_FORUM:
                ch = await client.get_chat(peer)

                if ch.type == ChatType.FORUM and message.chat.type != ch.type:
                    await message.reply(
                        "Both chats should have either forums(topics) enabled or disabled, however they are not."
                    )
                    return

            status_msg = await message.reply("Starting to forward messages...")

            message_ids = list(range(start_id, end_id + 1))
            total_messages = len(message_ids)
            logging.debug(f"Total messages to forward: {len(message_ids)}")

            messages_forwarded = 0

            is_group = message.chat.type in [
                ChatType.GROUP,
                ChatType.SUPERGROUP,
                ChatType.CHANNEL,
            ]
            delay = 3 if is_group else 1

            for i in range(0, len(message_ids), BATCH_SIZE):
                if STOP_EVENT.is_set():
                    await status_msg.edit(
                        f"[INFO] Forwarding interrupted! Successfully forwarded {messages_forwarded} messages before stopping."
                    )
                    return
                batch_ids = message_ids[i : i + BATCH_SIZE]
                # This is workaround for bots since they can't directly fetch whole chat history from a channel/group
                messages = await client.get_messages(peer, batch_ids)
                logging.debug(f"Fetched {len(messages)} messages in this batch")  # type: ignore
                logging.debug(f"Messages: {messages}")

                valid_messages = [
                    msg
                    for msg in messages  # type: ignore
                    if msg is not None and not msg.empty and not msg.service
                ]

                if valid_messages:
                    batch_fwd_count = 0
                    for msg in valid_messages:
                        if STOP_EVENT.is_set():
                            break
                        try:
                            await client.forward_messages(
                                chat_id=message.chat.id,
                                message_ids=msg.id,
                                from_chat_id=peer,
                                drop_author=CLONE,
                            )
                            batch_fwd_count += 1
                        except Exception as e:
                            logging.warning(f"Could not forward message {msg.id}: {e}")

                        await asyncio.sleep(delay)

                    messages_forwarded += batch_fwd_count
                    await status_msg.edit(
                        f"Forwarded {messages_forwarded} of {total_messages} messages..."
                    )

            if not STOP_EVENT.is_set():
                await status_msg.edit(
                    f"✅ Forwarding complete! Successfully forwarded {messages_forwarded} messages."
                )
                await status_msg.delete()
            else:
                await status_msg.edit(
                    f"[INFO] Forwarding interrupted! Successfully forwarded {messages_forwarded} messages before stopping."
                )

        except Exception as e:
            logging.error(f"Error forwarding messages: {str(e)}")
            pass

    except ValueError:
        await message.reply("Please provide valid numeric chat_id and message IDs")


async def main():
    print("[INFO] Starting bot...")
    await client.start()
    print("[INFO] Bot started.")
    await STOP_EVENT.wait()
    await client.stop()
    print("[INFO] Bot stopped.")


if __name__ == "__main__":
    client.run(main())
