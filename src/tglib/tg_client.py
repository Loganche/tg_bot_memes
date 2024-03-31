# -*- coding: utf-8 -*-
# stdlib modules
import json
import logging
import datetime

from telethon import TelegramClient


class TGClientError(Exception):
    pass


class TGClient(TelegramClient):
    INITIAL_MSG_OFFSET = 5
    TG_BOT_NAME = 'MBerushiBot'
    TG_ADMIN_NAME = 'loganche'

    def __init__(
        self,
        session: str,
        api_id: int,
        api_hash: str,
        channels_file: str,
        db,
        tg_bot_token: str | None = None,
    ):
        if not tg_bot_token:
            super().__init__(session, api_id, api_hash)
        else:
            super().__init__(session, api_id, api_hash)
            super().start(bot_token=tg_bot_token)
            self.check_connection()
        self.db = db
        self.import_channels_file(channels_file)

    def check_connection(self):
        if super().is_connected():
            logging.info('Connected successfully')
        else:
            logging.error('Connection is lost')
            raise TGClientError

    def import_channels_file(self, channels_file):
        with open(channels_file, 'r', encoding='utf8') as json_file:
            self.channels = json.load(json_file)

    async def add_new_channels_db(self):
        to_add = []
        res = self.db.get_all_channels()
        channels_db = dict(res.fetchall())

        for channel in self.channels:
            tg_channel = await self.get_input_entity(channel['name'])
            if channels_db.get(tg_channel.channel_id, -1) == -1:
                to_add.append(tg_channel.channel_id)

        if to_add:
            self.db.insert_new_channels(
                list(zip(to_add, [0] * len(to_add)))
            )  # converting to list of tuples (channel_id, 0)

    async def crawl_channels(self):
        for channel in self.channels:
            await self.crawl_channel_messages(channel)

    async def crawl_channel_messages(self, channel):
        tg_channel = await self.get_input_entity(channel['name'])
        message_id = self.db.get_channel_offset(tg_channel.channel_id)

        if message_id == -1:
            logging.error(f'Channel {tg_channel.channel_id} not initialized, skipping...')
            return
        elif message_id == 0:
            # crawling only last messages - OFFSET for new channels with 0 offset
            messages = self.iter_messages(tg_channel, limit=self.INITIAL_MSG_OFFSET)
        else:
            messages = self.iter_messages(tg_channel, min_id=message_id)

        max_msg_id = message_id
        async for message in messages:
            max_msg_id = max(max_msg_id, message.id)
            if message.media:
                if channel['forward']:
                    await self.forward_messages(
                        self.TG_BOT_NAME, message, tg_channel, schedule=datetime.timedelta(0, 5)
                    )
                else:
                    await self.send_message(
                        self.TG_BOT_NAME, message, schedule=datetime.timedelta(0, 5)
                    )
            else:
                logging.info(f'Message {message.id} from channel {channel["name"]} has no media')

        if max_msg_id == message_id:
            logging.info(f'No new messages for channel {tg_channel.channel_id}')
            return

        self.db.update_channel_offset(tg_channel.channel_id, max_msg_id)
