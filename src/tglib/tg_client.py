# -*- coding: utf-8 -*-
# stdlib modules
import json
import logging
import datetime
from asyncio import sleep

from telethon import TelegramClient


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

    async def add_new_channels_db(self):
        to_add = []
        res = self.db.get_all_channels()
        channels_db = dict(res.fetchall())

        for channel in self.channels:
            tg_channel = await self.get_input_entity(channel['name'])
            if channels_db.get(tg_channel.channel_id) is None:
                to_add.append(tg_channel.channel_id)

        if to_add:
            self.db.insert_new_channels(
                list(zip(to_add, [0] * len(to_add)))
            )  # converting to list of tuples (channel_id, 0)

    async def add_new_admins_db(self):
        to_add = []
        res = self.db.get_all_admins()
        admins_db = dict(res.fetchall())

        for admin in self.admins:
            admin_entity = await self.get_input_entity(admin['name'])
            if admins_db.get(admin_entity.user_id) is None:
                to_add.append(admin_entity.user_id)

        if to_add:
            self.db.insert_new_admins(
                list(zip(to_add, [0] * len(to_add)))
            )  # converting to list of tuples (user_id, 0)

    async def crawl_channels(self):
        for channel in self.channels:
            await self.crawl_channel_messages(channel)

    async def crawl_channel_messages(self, channel):
        """
        Get tg channel name and offset
        Receive all messages from offset to now
        Iterate over messages and send them to admin
        Find max message and update offset
        """
        tg_channel = await self.get_input_entity(channel['name'])
        message_id = self.db.get_channel_offset(tg_channel.channel_id)

        messages = self.get_messages_from_offset(tg_channel, message_id)

        max_msg_id = message_id
        async for message in messages:
            max_msg_id = max(max_msg_id, message.id)
            if message.media:
                # decide to send to admin or to channel
                if self.ALLOW_FORCE_POSTING:
                    if channel['forward']:
                        await self.forward_messages(
                            entity=self.TG_CHANNEL_NAME,
                            messages=message,
                            schedule=datetime.timedelta(
                                days=0, seconds=self.MESSAGE_SCHEDULE_SECONDS
                            ),
                        )
                    else:
                        await self.send_message(
                            entity=self.TG_CHANNEL_NAME,
                            message=message,
                            schedule=datetime.timedelta(
                                days=0, seconds=self.MESSAGE_SCHEDULE_SECONDS
                            ),
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
            else:
                logging.info(f'Message {message.id} from channel {channel["name"]} has no media')

        if max_msg_id == message_id:
            logging.info(f'No new messages for channel {tg_channel.channel_id}')
            return

        self.db.update_channel_offset(tg_channel.channel_id, max_msg_id)

    async def crawl_admins(self):
        for admin in self.admins:
            await self.crawl_admin_reactions(admin)

    async def crawl_admin_reactions(self, admin):
        """
        Get admin chat and offset
        Receive all messages from offset to now
        Iterate over messages and send them to channel (if reactions good)
        Find max message and update offset
        """
        admin_entity = await self.get_input_entity(admin['name'])
        message_id = self.db.get_admin_offset(admin_entity.user_id)

        messages = self.get_messages_from_offset(admin_entity, message_id)

        max_msg_id = message_id
        async for message in messages:
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

        if max_msg_id == message_id:
            logging.info(f'No new reactions from admin {admin_entity.user_id}')
            return

        self.db.update_admin_offset(admin_entity.user_id, max_msg_id)
        return

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
