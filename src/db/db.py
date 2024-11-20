# -*- coding: utf-8 -*-
# stdlib modules
import logging
import sqlite3
from contextlib import contextmanager


class Sqlite3:
    TIMEOUT = 10

    def __init__(self, db_name: str) -> None:
        self.db_name = db_name
        self.connection: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None
        self._connect()
        self.check_tables()

    def _connect(self):
        """Establish a database connection."""
        self.connection = sqlite3.connect(self.db_name, timeout=self.TIMEOUT)
        self.cursor = self.connection.cursor()

    def _disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

    @contextmanager
    def transaction(self):
        """Provide a transactional scope for database operations."""
        try:
            yield
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logging.error(f'Transaction failed: {e}')
            raise

    def check_tables(self):
        """Ensure required tables exist."""
        with self.transaction():
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS channels
                                (channel_id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL)"""
            )
            self.cursor.execute(
                """CREATE TABLE IF NOT EXISTS admins
                                (user_id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL)"""
            )
        logging.info('Initialized tables.')

    def insert(self, table, values):
        """Insert a single row."""
        placeholders = ', '.join(['?'] * len(values))
        query = f'INSERT INTO {table} VALUES ({placeholders})'
        with self.transaction():
            self.cursor.execute(query, values)

    def bulk_insert(self, table, rows):
        """Insert multiple rows."""
        placeholders = ', '.join(['?'] * len(rows[0]))
        query = f'INSERT INTO {table} VALUES ({placeholders})'
        with self.transaction():
            self.cursor.executemany(query, rows)

    def update(self, table, set_column, set_value, where_column, where_value):
        """Update rows in the table."""
        query = f'UPDATE {table} SET {set_column}=? WHERE {where_column}=?'
        with self.transaction():
            self.cursor.execute(query, (set_value, where_value))

    def fetch_all(self, table, columns, conditions=None):
        """Fetch rows with optional conditions."""
        query = f'SELECT {", ".join(columns)} FROM {table}'
        if conditions:
            query += f' WHERE {conditions}'
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def fetch_one(self, table, column, conditions=None):
        """Fetch a single value."""
        query = f'SELECT {column} FROM {table}'
        if conditions:
            query += f' WHERE {conditions}'
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        return result[0] if result else -1

    def __del__(self):
        self._disconnect()
