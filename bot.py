# -*- coding: utf-8 -*-
# local modules
from src import TGClient, load_env

config = load_env()
client = TGClient(session='anon', api_id=config['API_ID'], api_hash=config['API_HASH'])


async def main():
    berushi_channel = await client.get_input_entity('m_berushi')
    messages = client.iter_messages(berushi_channel, limit=3)  # breaks if set reverse=True
    async for message in messages:
        if message.media:
            await client.send_message(
                'me', 'Мем смешной' if not message.text else message.text, file=message.photo
            )
        else:
            await client.send_message('me', 'Мем смешной' if not message.text else message.text)


with client:
    client.loop.run_until_complete(main())
