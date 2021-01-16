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

import os
import sys
import argparse
import logging.config

from dotenv import load_dotenv

from bot import Overlord, UserSyncExtension
from ranking import RankingExtension
from db.models.stat import UserStatType
from util import ConfigView
from db import DBSession, EventType
from db.predefined import EVENT_TYPES, USER_STAT_TYPES

def main(argv):
    # Load env variables
    load_dotenv()

    # Parse arguments
    parser = argparse.ArgumentParser(description='Overlord Discord Bot')
    parser.add_argument('-c', '--config', nargs='?', type=str, default='config.json', help='config path')
    args = parser.parse_args(argv[1:])

    # Load config
    config = ConfigView(path=args.config, schema_name="config_schema")

    # Apply logging config
    if config['logger']:
        logging.config.dictConfig(config['logger'])

    # Init database
    url = os.getenv('DATABASE_ACCESS_URL')
    if 'sqlite' in url:
        import db.queries as q
        q.MODE = q.MODE_SQLITE
    session = DBSession(url, autocommit=False)
    session.sync_table(EventType, 'name', EVENT_TYPES)
    session.sync_table(UserStatType, 'name', USER_STAT_TYPES)

    # Init bot
    discord_bot = Overlord(config.bot, session)

    # Init extensions
    user_sync_ext = UserSyncExtension(bot=discord_bot)
    ranking_ext = RankingExtension(bot=discord_bot, priority=1)

    # Attach extensions
    discord_bot.extend(user_sync_ext)
    discord_bot.extend(ranking_ext)

    # Start bot
    discord_bot.run()

    return 0

if __name__ == "__main__":
    res = main(sys.argv)
    exit(res)
