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

    def get_all(self, columns, table):
        res = self.cursor.execute(f'SELECT {", ".join(i for i in columns)} FROM {table}')
        self.connection.commit()
        return res

    def get_offset(self, table, where, arg):
        res = self.cursor.execute(f'SELECT message_id FROM {table} WHERE {where}=?', [arg])
        self.connection.commit()
        try:
            message_id = res.fetchone()[0]
        except Exception:
            message_id = -1
        return message_id

    def insert_new(self, table, values):
        logging.info(f'Adding {len(values)} new {table} from file')
        self.cursor.executemany(f'INSERT INTO {table} VALUES (?, ?)', values)
        self.connection.commit()

    def update_offset(self, table, where, where_id, message_id):
        logging.info(f'Updating {table} {where_id} offset with message {message_id}')
        self.cursor.execute(
            f'UPDATE {table} SET message_id=? WHERE {where}=?', [message_id, where_id]
        )
        self.connection.commit()
