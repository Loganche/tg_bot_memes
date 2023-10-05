# -*- coding: utf-8 -*-
# stdlib modules
import os

from dotenv import load_dotenv
from telethon import TelegramClient


def load_env():
    # refactor because shit
    load_dotenv('.env')
    api_id = os.environ['API_ID']
    api_hash = os.environ['API_HASH']
    bot_token = os.environ['BOT_TOKEN']
    return int(api_id), api_hash, bot_token


api_id, api_hash, bot_token = load_env()
client = TelegramClient('anon', api_id, api_hash).start(bot_token=bot_token)


async def main():
    for _ in range(10):
        await client.send_message('loganche', 'Testing Telethon!')
        await client.send_message('Lesha4', 'когда покур')


with client:
    client.loop.run_until_complete(main())
