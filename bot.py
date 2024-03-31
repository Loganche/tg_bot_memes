# -*- coding: utf-8 -*-
# stdlib modules
import logging
from asyncio import sleep
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

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
    db=db,
    tg_bot_token=config['BOT_TOKEN'],
)
killer = GracefulKiller()
scheduler = AsyncIOScheduler()


async def main():
    try:
        client.check_connection()
    except TGClientError:
        logging.error('Got error from TG Client, exiting...')
        db.connection.close()
        exit(-1)
    await client.add_new_channels_db()

    while not killer.kill_now:
        logging.info(
            f'Running crawl_channels(), next run at {datetime.now()+timedelta(seconds=10)}'
        )
        await client.crawl_channels()
        await sleep(10)

    db.connection.close()
    logging.info('Stopping...')


with client:
    client.loop.run_until_complete(main())


# comment everytinhg below and uncomment previous code to run in while loop instead AsyncScheduler
# scheduler.add_job(main)
# scheduler.add_job(client.crawl_channels, 'interval', seconds=10)
# scheduler.start()
# with client:
#     client.loop.run_forever()
# db.connection.close()
# logging.info('Stopping...')
