# -*- coding: utf-8 -*-
# stdlib modules
import logging

from telethon import TelegramClient


class TGClientError(Exception):
    pass


class TGClient(TelegramClient):
    def __init__(self, session: str, api_id: int, api_hash: str, tg_bot_token: str | None = None):
        if not tg_bot_token:
            super().__init__(session, api_id, api_hash)
        else:
            super().__init__(session, api_id, api_hash)
            super().start(bot_token=tg_bot_token)
            self.check_connection()

    def check_connection(self) -> bool:
        if super().is_connected():
            logging.info('Connected successfully')
        else:
            logging.error('Connection is lost')
            raise TGClientError
