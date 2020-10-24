#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
#........../\./\...___......|\.|..../...\.........#
#........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
#......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2020 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

import sys
import argparse
import bot
import logging.config

from dotenv import load_dotenv

from util import ConfigView
from db import SQLiteSession, EventType
from db.predefined import EVENT_TYPES

def main(argv):
    # Load env variables
    load_dotenv()

    # Parse arguments
    parser = argparse.ArgumentParser(description='Overlord Discord Bot')
    parser.add_argument('-c', '--config', nargs='?', type=str, default='config.json', help='config path')
    args = parser.parse_args(argv[1:])

    # Load config
    config = ConfigView(args.config)

    # Apply logging config
    if config['logger']:
        logging.config.dictConfig(config['logger'])

    # Init database
    session = SQLiteSession("test.db", autocommit=False)
    session.sync_table(EventType, 'name', EVENT_TYPES)
    session.commit()

    # Init bot
    discord_bot = bot.Overlord(config.bot, session)
    discord_bot.run()

    return 0

if __name__ == "__main__":
    res = main(sys.argv)
    exit(res)
