# -*- coding: utf-8 -*-
# stdlib modules
import logging
import sqlite3


class Sqlite3:
    TIMEOUT = 10

    def __init__(self, db_name) -> None:
        self.connection = sqlite3.connect(db_name, timeout=self.TIMEOUT)
        self.cursor = self.connection.cursor()
        self.check_tables()

    def check_tables(self):
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS channels
                            (channel_id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL)'''
        )
        self.cursor.execute(
            '''CREATE TABLE IF NOT EXISTS admins
                            (user_id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL)'''
        )
        self.connection.commit()
        res = self.cursor.execute('SELECT name FROM sqlite_master')
        logging.info(f'Got tables: {res.fetchall()}')

    def get_all_channels(self):
        res = self.cursor.execute('SELECT channel_id, message_id FROM channels')
        self.connection.commit()
        return res

    def get_all_admins(self):
        res = self.cursor.execute('SELECT user_id, message_id FROM admins')
        self.connection.commit()
        return res

    def get_channel_offset(self, channel_id):
        res = self.cursor.execute(
            'SELECT message_id FROM channels WHERE channel_id=?', [channel_id]
        )
        self.connection.commit()
        try:
            message_id = res.fetchone()[0]
        except Exception:
            message_id = -1
        return message_id

    def get_admin_offset(self, user_id):
        res = self.cursor.execute('SELECT message_id FROM admins WHERE user_id=?', [user_id])
        self.connection.commit()
        try:
            message_id = res.fetchone()[0]
        except Exception:
            message_id = -1
        return message_id

    def insert_new_channels(self, values):
        logging.info(f'Adding {len(values)} new channels from file')
        self.cursor.executemany('INSERT INTO channels VALUES (?, ?)', values)
        self.connection.commit()

    def insert_new_admins(self, values):
        logging.info(f'Adding {len(values)} new admins from file')
        self.cursor.executemany('INSERT INTO admins VALUES (?, ?)', values)
        self.connection.commit()

    def update_channel_offset(self, channel_id, message_id):
        logging.info(f'Updating channel {channel_id} offset with message {message_id}')
        self.cursor.execute(
            'UPDATE channels SET message_id=? WHERE channel_id=?', [message_id, channel_id]
        )
        self.connection.commit()

    def update_admin_offset(self, user_id, message_id):
        logging.info(f'Updating admin {user_id} offset with message {message_id}')
        self.cursor.execute('UPDATE admins SET message_id=? WHERE user_id=?', [message_id, user_id])
        self.connection.commit()
