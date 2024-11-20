# -*- coding: utf-8 -*-
# stdlib modules
import logging
from asyncio import sleep
from argparse import ArgumentParser
from datetime import datetime, timedelta
from functools import partial

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
        db._disconnect()
        exit(-1)
    await client.add_new_entities_db(['channel_id', 'message_id'], 'channels', client.channels)
    await client.add_new_entities_db(['user_id', 'message_id'], 'admins', client.admins)

    while not killer.kill_now:
        logging.info(f'Crawling, next run at {datetime.now()+timedelta(seconds=10)}')
        await client.crawl_entities(
            client.channels,
            partial(
                client.crawl_entity_messages,
                table='channels',
                where_column='channel_id',
                message_function=client.send_channel_message,
            ),
        )
        await client.crawl_entities(
            client.admins,
            partial(
                client.crawl_entity_messages,
                table='admins',
                where_column='user_id',
                message_function=client.check_admin_reaction,
            ),
        )
        await sleep(10)

    db.connection.close()
    logging.info('Stopping...')


with client:
    client.loop.run_until_complete(main())
