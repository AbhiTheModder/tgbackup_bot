from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, MessageService
import logging
from configparser import ConfigParser

# basic logs
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

cfg = ConfigParser()
cfg.read("config.ini")

# grab all the config stuff
API_ID = int(cfg.get("Telegram", "api_id"))
API_HASH = cfg.get("Telegram", "api_hash")
BOT_TOKEN = cfg.get("Telegram", "bot_token")
CLONE = cfg.getboolean("Telegram", "clone")
BATCH_SIZE = cfg.getint("Telegram", "batch_size")  # how many msgs per batch

# retry_delay for auto handling floodwaits
client = TelegramClient('forward_bot_session', API_ID, API_HASH, 
                       retry_delay=1, auto_reconnect=True)

@client.on(events.NewMessage(pattern="/start"))
async def start_command(event):
    await event.respond("Hi! Use /forward chat_id start_id end_id to forward stuff")

@client.on(events.NewMessage(pattern="/forward"))
async def forward_messages(event):
    # parse the command
    stuff = event.message.text.strip().split()
    if len(stuff) != 4:
        await event.respond("Wrong format! Use: /forward chat_id start_id end_id")
        return

    try:
        chat = int(stuff[1])
        start = int(stuff[2])
        end = int(stuff[3])
    except:
        await event.respond("Numbers only!")
        return

    # figure out the peer type
    if chat < 0:
        if str(chat).startswith("-100"):
            peer = PeerChannel(int(str(chat)[4:]))
        else:
            peer = PeerChat(-chat)
    else:
        peer = PeerUser(chat)

    try:
        status = await event.respond("Starting...")
        msg_range = range(start, end + 1)
        total = len(msg_range)
        done = 0

        # do the forwarding
        for i in range(0, total, BATCH_SIZE):
            chunk = msg_range[i:i + BATCH_SIZE]
            msgs = await client.get_messages(peer, ids=chunk)
            
            # skip service messages
            real_msgs = [m for m in msgs if m and not isinstance(m, MessageService)]
            
            if real_msgs:
                # telethon handles floodwait automatically now
                await client.forward_messages(
                    event.chat_id,
                    real_msgs,
                    from_peer=peer,
                    drop_author=CLONE,
                    silent=True
                )
                done += len(real_msgs)
                await status.edit(f"Forwarded {done}/{total} messages...")

        await status.edit(f"Done! Forwarded {done} messages")
    except Exception as e:
        print(f"Oops: {e}")
        await event.respond(f"Something broke: {str(e)}")

def main():
    print("Bot starting...")
    client.start(bot_token=BOT_TOKEN)
    print("Ready to forward!")
    client.run_until_disconnected()

if __name__ == "__main__":
    main()

# TODO: add progress bar maybe?
# abhi pls test i didn't test