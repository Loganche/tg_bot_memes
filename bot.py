# -*- coding: utf-8 -*-
# stdlib modules
import logging
from asyncio import sleep
from argparse import ArgumentParser
from datetime import datetime, timedelta

# local modules
from src.db.db import Sqlite3
from src.preloader import load_env, load_config
from src.tglib.tg_client import TGClient, TGClientError
from src.appkiller.killer import GracefulKiller

parser = ArgumentParser(description='Telegram bot for parsing and posting messages.')
parser.add_argument(
    '--env-file',
    action='store',
    type=str,
    default='.env',
    help='path to environment file (default .env)',
)
parser.add_argument(
    '--db-file',
    action='store',
    type=str,
    default='data.db',
    help='path to sqlite3 .db file (default data.db)',
)
parser.add_argument(
    '--config-file',
    action='store',
    type=str,
    default='config.json',
    help='path to config file (default config.json)',
)

args = parser.parse_args()
args = vars(args)
logging.info(args)

env = load_env(args['env_file'])
config = load_config(args['config_file'])
db = Sqlite3(args['db_file'])
client = TGClient(
    session='anon',
    api_id=env['API_ID'],
    api_hash=env['API_HASH'],
    config=config,
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
