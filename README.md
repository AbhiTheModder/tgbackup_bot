# Telegram Bot

A Telegram Message forward or backup or clone ( or whatever you want to call it) bot.

A Telegram bot that helps you forward messages from one chat to another in batches, without the risk of getting banned that comes with using userbot accounts.


## Features

- Forward messages between chats, groups, and channels
- Batch processing to handle large message volumes efficiently
- Progress tracking with status updates
- Supports forwarding from public and private chats
- Skips service messages automatically
- Rate-limit friendly implementation
- Minimal dependencies and easy setup
- Faster than userbots and less likely to get banned

## Setup

1. Clone this repository
2. Copy example_config.ini to config.ini
3. Fill in your Telegram API credentials in config.ini:
   ```ini
   [Telegram]
   api_id = YOUR_API_ID
   api_hash = YOUR_API_HASH
   bot_token = YOUR_BOT_TOKEN
   clone = True # Set to False to disable message cloning
   batch_size = 100 # Number of messages to forward per batch
   ```
   Message cloning means that the bot will send a copy of the message to the destination chat, preserving the original message's content, without author's tag/quote.

To get your credentials:
- Create an application at https://my.telegram.org/apps
- Create a bot through @BotFather to get the bot token

## Usage

1. Start the bot:
```sh
python bot.py
```

2. Send `/start` to your bot to get usage instructions

3. Use the `/forward` command with the following format:
```
/forward chat_id start_id end_id
```
Example:
```
/forward -1002540899531 1 70056
```

Where:
- `chat_id`: Source chat ID (can be negative for channels/groups)
- `start_id`: First message ID to forward
- `end_id`: Last message ID to forward

## Requirements

- Python 3.10+
- Pyro~gram~fork
- tgcrypto
- ConfigParser (built-in)

```sh
pip install pyrofork tgcrypto
```

## Notes

- The bot must be a member of both source and destination chats
- For channels/groups, use the chat ID format: -100xxxxxxxxxx
- For users: positive integer ID
