# -*- coding: utf-8 -*-
# stdlib modules
import json
import logging
import datetime
from asyncio import sleep

from telethon import TelegramClient
from telethon.tl.types import InputPeerUser, InputPeerChannel

# local modules
from src.db.db import Sqlite3


class TGClientError(Exception):
    pass


class TGClient(TelegramClient):
    INITIAL_MESSAGE_OFFSET = 5
    MESSAGE_SCHEDULE_SECONDS = 5
    REACTIONS_APPROVED_AMOUNT = 1
    ALLOW_FORCE_POSTING = False
    TG_CHANNEL_NAME = ''

    def __init__(
        self,
        session: str,
        api_id: int,
        api_hash: str,
        config: dict,
        db: Sqlite3,
        tg_bot_token: str | None = None,
    ):
        if not tg_bot_token:
            super().__init__(session, api_id, api_hash)
        else:
            super().__init__(session, api_id, api_hash)
            super().start(bot_token=tg_bot_token)
            self.check_connection()
        self.db = db
        self.channels = config['channels']
        self.admins = config['admins']
        self.INITIAL_MESSAGE_OFFSET = config['initial_offset']
        self.MESSAGE_SCHEDULE_SECONDS = config['schedule_seconds']
        self.REACTIONS_APPROVED_AMOUNT = config['reactions_approved_amount']
        self.TG_CHANNEL_NAME = config['channel_name']
        self.ALLOW_FORCE_POSTING = config['allow_force_posting']

    def check_connection(self):
        if super().is_connected():
            logging.info('Connected successfully')
        else:
            logging.error('Connection is lost')
            raise TGClientError

    def get_input_entity_id(self, input_entity):
        if isinstance(input_entity, InputPeerChannel):
            return input_entity.channel_id
        elif isinstance(input_entity, InputPeerUser):
            return input_entity.user_id
        return 0

    async def add_new_entities_db(self, columns, table, entities):
        to_add = []
        res = self.db.get_all(columns=columns, table=table)
        db = dict(res.fetchall())

        for entity in entities:
            input_entity = await self.get_input_entity(entity['name'])
            input_entity_id = self.get_input_entity_id(input_entity)
            if db.get(input_entity_id) is None:
                to_add.append(input_entity_id)

        if to_add:
            self.db.insert_new(
                table=table, values=list(zip(to_add, [0] * len(to_add)))
            )  # converting to list of tuples (channel_id, 0)

    async def crawl_entities(self, entities, crawl_function):
        for entity in entities:
            await crawl_function(entity)

    def get_messages_from_offset(self, entity, offset_message_id):
        kwargs = {'entity': entity}
        if offset_message_id == -1:
            logging.error(f'Entity {entity.id} not initialized, skipping...')
            return
        elif offset_message_id == 0:
            # crawling only last messages - OFFSET for new channels with 0 offset
            kwargs['limit'] = self.INITIAL_MESSAGE_OFFSET
        else:
            kwargs['min_id'] = offset_message_id
        return self.iter_messages(**kwargs)

    async def crawl_entity_messages(self, entity, table, where_id, message_function):
        """
        Get tg channel name and offset
        Receive all messages from offset to now
        Iterate over messages and send them to admin
        Find max message and update offset
        """
        input_entity = await self.get_input_entity(entity['name'])
        input_entity_id = self.get_input_entity_id(input_entity)
        message_id = self.db.get_offset(table=table, where=where_id, arg=input_entity_id)

        messages = self.get_messages_from_offset(input_entity, message_id)

        max_msg_id = message_id
        async for message in messages:
            # self.send_channel_message(message, max_msg_id, entity)
            # self.check_admin_reaction(message, max_msg_id, entity)
            max_msg_id = await message_function(message, max_msg_id, entity)

        if max_msg_id == message_id:
            logging.info(f'No new messages for {table} {input_entity_id}')
            return

        self.db.update_offset(
            table=table,
            where=where_id,
            where_id=input_entity_id,
            message_id=max_msg_id,
        )

    async def send_channel_message(self, message, max_msg_id, channel):
        max_msg_id = max(max_msg_id, message.id)
        if message.media:
            # decide to send to admin or to channel
            if self.ALLOW_FORCE_POSTING:
                if channel['forward']:
                    await self.forward_messages(
                        entity=self.TG_CHANNEL_NAME,
                        messages=message,
                        schedule=datetime.timedelta(days=0, seconds=self.MESSAGE_SCHEDULE_SECONDS),
                    )
                else:
                    message.message = 'Отправлено ботом'
                    await self.send_message(
                        entity=self.TG_CHANNEL_NAME,
                        message=message,
                        schedule=datetime.timedelta(days=0, seconds=self.MESSAGE_SCHEDULE_SECONDS),
                    )
            else:
                for admin in self.admins:
                    if channel['forward']:
                        await self.forward_messages(
                            entity=admin['name'],
                            messages=message,
                        )
                    else:
                        await self.send_message(
                            entity=admin['name'],
                            message=message,
                        )
        return max_msg_id

    async def check_admin_reaction(self, message, max_msg_id, entity):
        if message.reactions:
            reactions = {x.reaction.emoticon: x.count for x in message.reactions.results}
            if reactions.get('👍', 0) == self.REACTIONS_APPROVED_AMOUNT:
                await self.send_message(
                    entity=self.TG_CHANNEL_NAME,
                    message=message,
                    schedule=datetime.timedelta(days=0, seconds=self.MESSAGE_SCHEDULE_SECONDS),
                )
            max_msg_id = (
                max(max_msg_id, message.id)
                if reactions.get('👍') is not None or reactions.get('👎') is not None
                else max_msg_id
            )
        return max_msg_id
