# -*- coding: utf-8 -*-
# stdlib modules
import sys
import json
import logging

from dotenv import dotenv_values

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s : %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    stream=sys.stdout,
    level=logging.INFO,
)


def load_env(env_file: str):
    # refactor because shit
    return dotenv_values(env_file)


def load_config(config_file: str):
    with open(config_file, 'r', encoding='utf8') as json_file:
        data = json.load(json_file)
    return data
