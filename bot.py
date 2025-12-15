import asyncio
import logging
import os
import signal
from configparser import ConfigParser

from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.errors import ChatWriteForbidden
from pyrogram.types import Chat, Message

STOP_EVENT = asyncio.Event()
logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)
signal.signal(signal.SIGINT, lambda _, __: STOP_EVENT.set())


def get_bool_env(env_var, fallback):
    env_val = os.getenv(env_var)
    if env_val is not None:
        return env_val.lower() in ("true", "y", "1", "yes", "on")
    return fallback


config = ConfigParser()
config.read("config.ini")

CLONE = get_bool_env("CLONE", config.getboolean("Telegram", "clone"))
AUTO_BACKUP = get_bool_env("AUTO_BACKUP", config.getboolean("Telegram", "auto_backup"))
WITH_FORUM = get_bool_env("WITH_FORUM", config.getboolean("Telegram", "with_forum"))

API_ID = int(os.getenv("API_ID", config.get("Telegram", "api_id")))
API_HASH = os.getenv("API_HASH", config.get("Telegram", "api_hash"))
BOT_TOKEN = os.getenv("BOT_TOKEN", config.get("Telegram", "bot_token"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", config.get("Telegram", "batch_size")))
TARGET_CHAT = int(os.getenv("TARGET_CHAT", config.get("Telegram", "target_chat")))
SOURCE_CHAT = int(os.getenv("SOURCE_CHAT", config.get("Telegram", "source_chat")))
USER_TOKEN = os.getenv("USER_TOKEN", config.get("Telegram", "user_token"))

client = Client("backup_bot", API_ID, API_HASH, bot_token=BOT_TOKEN)
user_acc = None
if WITH_FORUM and USER_TOKEN:
    user_acc = Client("my_acc", API_ID, API_HASH, session_string=USER_TOKEN)
elif WITH_FORUM:
    exit("[ERROR] user_token is necessary to use forum features")

auto_backup = filters.create(lambda _, __, ___: AUTO_BACKUP)
SOURCE_CHAT = (
    SOURCE_CHAT
    if str(SOURCE_CHAT).startswith("-100")
    else int("-100" + str(SOURCE_CHAT))
)
TARGET_CHAT = (
    TARGET_CHAT
    if str(TARGET_CHAT).startswith("-100")
    else int("-100" + str(TARGET_CHAT))
)


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
                peer = chat_id
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
                            if WITH_FORUM:
                                await handle_forum(msg, message.chat, client, peer)
                            else:
                                await client.forward_messages(
                                    chat_id=message.chat.id,
                                    message_ids=msg.id,
                                    from_chat_id=peer,
                                    drop_author=CLONE,
                                )
                            batch_fwd_count += 1
                        except ChatWriteForbidden:
                            await status_msg.edit(
                                "ChatWriteForbidden: Please make sure i've been given admin rights"
                            )
                            return
                        except Exception as e:
                            import traceback

                            logging.warning(f"Could not forward message {msg.id}: {e}")
                            traceback.print_exc()

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


@client.on_message(
    auto_backup & filters.incoming & filters.chat(SOURCE_CHAT) & ~filters.service
)
async def auto_forward_new_message(client: Client, message: Message):
    if message.empty:
        return
    try:
        if WITH_FORUM and message.is_topic_message and hasattr(message, "topic"):
            trgt_chat = await client.get_chat(TARGET_CHAT)
            await handle_forum(message, trgt_chat, client, SOURCE_CHAT)  # type: ignore
        else:
            await client.forward_messages(
                chat_id=TARGET_CHAT,
                message_ids=message.id,
                from_chat_id=SOURCE_CHAT,
                drop_author=CLONE,
            )
    except ChatWriteForbidden:
        logging.warning(
            "ChatWriteForbidden: Make sure the bot has admin rights in the target chat."
        )
    except Exception as e:
        logging.error(f"Failed to auto-forward message {message.id}: {e}")


async def handle_forum(msg: Message, trgt_chat: Chat, client: Client, peer: int):
    topics = [
        topic
        async for topic in user_acc.get_forum_topics(trgt_chat.id)  # type: ignore
    ]
    if msg.is_topic_message and hasattr(msg, "topic"):
        topic_title = msg.topic.title  # type: ignore
        if not any(topic.title == topic_title for topic in topics):
            new_topic = await client.create_forum_topic(trgt_chat.id, topic_title)
            await client.forward_messages(
                chat_id=trgt_chat.id,
                message_ids=msg.id,
                from_chat_id=peer,
                drop_author=CLONE,
                message_thread_id=new_topic.id,
            )
        else:
            new_topic = next(topic for topic in topics if topic.title == topic_title)
            await client.forward_messages(
                chat_id=trgt_chat.id,
                message_ids=msg.id,
                from_chat_id=peer,
                drop_author=CLONE,
                message_thread_id=new_topic.id,
            )
    else:
        await client.forward_messages(
            chat_id=trgt_chat.id,
            message_ids=msg.id,
            from_chat_id=peer,
            drop_author=CLONE,
            message_thread_id=1,
        )


async def main():
    print("[INFO] Starting bot...")
    await client.start()
    if user_acc:
        await user_acc.start()
    print("[INFO] Bot started.")
    await STOP_EVENT.wait()
    await client.stop()
    if user_acc:
        await user_acc.stop()
    print("[INFO] Bot stopped.")


if __name__ == "__main__":
    client.run(main())
