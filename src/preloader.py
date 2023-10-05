# -*- coding: utf-8 -*-
# stdlib modules
import sys
import logging

from dotenv import dotenv_values

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s : %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    stream=sys.stdout,
    level=logging.INFO,
)


def load_env():
    # refactor because shit
    return dotenv_values('.env')
