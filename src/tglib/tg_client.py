# -*- coding: utf-8 -*-
# stdlib modules
import json
import logging
import datetime
from asyncio import PriorityQueue

from telethon import TelegramClient
from telethon.errors import RPCError
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
        self.MAX_NEW_MESSAGES = config['max_new_messages']
        self.bot_token = tg_bot_token
        self.start_bot()

    def start_bot(self):
        if self.bot_token:
            try:
                self.start(bot_token=self.bot_token)
                self.check_connection()
            except RPCError as e:
                logging.error(f'Failed to start bot: {e}')
                raise TGClientError('Bot connection failed.')

    def check_connection(self):
        if not self.is_connected():
            logging.error('Connection lost.')
            raise TGClientError('Connection failed.')
        logging.info('Connected successfully.')

    def get_input_entity_id(self, input_entity):
        if isinstance(input_entity, InputPeerChannel):
            return input_entity.channel_id
        elif isinstance(input_entity, InputPeerUser):
            return input_entity.user_id
        return 0

    async def add_new_entities_db(self, columns, table, entities):
        to_add = []
        db = dict(self.db.fetch_all(columns=columns, table=table))

        for entity in entities:
            try:
                input_entity = await self.get_input_entity(entity['name'])
                entity_id = self.get_input_entity_id(input_entity)
                if db.get(entity_id) is None:
                    to_add.append((entity_id, 0))
            except Exception as e:
                logging.warning(f"Failed to process entity {entity['name']}: {e}")

        if to_add:
            self.db.bulk_insert(table=table, rows=to_add)
            logging.info(f'Added {len(to_add)} new entities to {table}.')

    async def crawl_entities(self, entities, process_entity_func):
        for entity in entities:
            try:
                await process_entity_func(entity)
            except Exception as e:
                logging.error(f"Error crawling entity {entity['name']}: {e}")

    def get_messages_with_offset(self, entity, offset_message_id):
        kwargs = {'entity': entity}
        if offset_message_id == -1:
            logging.error(f'Entity {entity.id} not initialized, skipping...')
            return
        elif offset_message_id == 0:
            # crawling only last messages - OFFSET for new channels with 0 offset
            kwargs['limit'] = self.INITIAL_MESSAGE_OFFSET
        else:
            kwargs['min_id'] = offset_message_id
        try:
            return self.iter_messages(**kwargs)
        except RPCError as e:
            logging.error(f"Failed to fetch messages for {entity['name']}: {e}")
            return []

    async def get_max_new_messages(self, messages):
        views_queue = PriorityQueue(maxsize=self.MAX_NEW_MESSAGES)

        async for message in messages:
            if views_queue.full():
                min_view_count, tmp_message = await views_queue.get()
                if min_view_count > message.views:
                    await views_queue.put((min_view_count, tmp_message))
                else:
                    await views_queue.put((message.views, message))
            else:
                await views_queue.put((message.views, message))

        new_messages = []
        while not views_queue.empty():
            _, message = await views_queue.get()
            new_messages.append(message)
        new_messages.sort(key=lambda msg: msg.id)

        return new_messages

    async def crawl_entity_messages(self, entity, table, where_column, process_message):
        """
        Get tg channel name and offset
        Receive all messages from offset to now
        Iterate over messages and send them to admin
        Find max message and update offset
        """
        input_entity = await self.get_input_entity(entity['name'])
        input_entity_id = self.get_input_entity_id(input_entity)
        offset_message_id = self.db.fetch_one(
            table=table, column='message_id', conditions=f'{where_column}={input_entity_id}'
        )

        messages = self.get_messages_with_offset(input_entity, offset_message_id)
        messages = await self.get_max_new_messages(messages)
        max_message_id = offset_message_id

        async for message in messages:
            try:
                max_message_id = await process_message(message, max_message_id, entity)
            except Exception as e:
                logging.error(f'Error processing message {message.id}: {e}')

        if max_message_id > offset_message_id:
            self.db.update(
                table=table,
                set_column='message_id',
                set_value=max_message_id,
                where_column=where_column,
                where_value=input_entity_id,
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
