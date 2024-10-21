# -*- coding: utf-8 -*-
# stdlib modules
import logging
from asyncio import sleep
from datetime import datetime, timedelta

# local modules
from src.db.db import Sqlite3
from src.preloader import load_env
from src.tglib.tg_client import TGClient, TGClientError
from src.appkiller.killer import GracefulKiller

config = load_env()
db = Sqlite3('data.db')
client = TGClient(
    session='anon',
    api_id=config['API_ID'],
    api_hash=config['API_HASH'],
    channels_file='channels.json',
    admins_file='admins.json',
    db=db,
)
killer = GracefulKiller()


async def main():
    try:
        client.check_connection()
    except TGClientError:
        logging.error('Got error from TG Client, exiting...')
        db.connection.close()
        exit(-1)
    await client.add_new_channels_db()
    await client.add_new_admins_db()

    while not killer.kill_now:
        logging.info(f'Crawling, next run at {datetime.now()+timedelta(seconds=10)}')
        await client.crawl_channels()
        await client.crawl_admins()
        await sleep(10)

    db.connection.close()
    logging.info('Stopping...')


with client:
    client.loop.run_until_complete(main())
