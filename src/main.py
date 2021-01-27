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

from dotenv import load_dotenv

from util import ConfigView, ConfigManager
from util.logger import LoggerRootConfig, update_config as update_logger
from db import DBSession, EventType, UserStatType
from db.predefined import EVENT_TYPES, USER_STAT_TYPES
from overlord import Overlord, OverlordRootConfig
from extensions import UtilityExtension, RankingExtension, ConfigExtension, StatsExtension, InviteExtension
from extensions import RankingRootConfig, InviteRootConfig

class ExtensionsConfig(ConfigView):
    """
    extension {
        rank   : RankingRootConfig
        invite : InviteRootConfig
    }
    """
    rank   : RankingRootConfig = RankingRootConfig()
    invite : InviteRootConfig  = InviteRootConfig()

class RootConfig(ConfigView):
    """
    logger      : LoggerRootConfig
    bot         : OverlordRootConfig
    extension   : ExtensionsConfig
    """
    logger    : LoggerRootConfig   = LoggerRootConfig()
    bot       : OverlordRootConfig = OverlordRootConfig()
    extension : ExtensionsConfig   = ExtensionsConfig()

class Configuration(ConfigManager):

    config : RootConfig

    def alter(self, raw: str) -> None:
        super().alter(raw)
        update_logger(self.config.logger)


def main(argv):
    # Load env variables
    load_dotenv()

    # Parse arguments
    parser = argparse.ArgumentParser(description='Overlord Discord Bot')
    parser.add_argument('-c', '--config', nargs='?', type=str, default='overlord.cfg', help='config path')
    args = parser.parse_args(argv[1:])

    # Load config
    cnf_manager = Configuration(args.config)

    # Init database
    url = os.getenv('DATABASE_ACCESS_URL')
    if 'sqlite' in url:
        import db.queries as q
        q.MODE = q.MODE_SQLITE
    session = DBSession(url, autocommit=False)
    session.sync_table(EventType, 'name', EVENT_TYPES)
    session.sync_table(UserStatType, 'name', USER_STAT_TYPES)

    # Init bot
    discord_bot = Overlord(cnf_manager, session)

    # Init extensions
    extras_ext = UtilityExtension(bot=discord_bot)
    stats_ext = StatsExtension(bot=discord_bot)
    ranking_ext = RankingExtension(bot=discord_bot, priority=1)
    conf_ext = ConfigExtension(bot=discord_bot)
    invite_ext = InviteExtension(bot=discord_bot)

    # Attach extensions
    discord_bot.extend(extras_ext)
    discord_bot.extend(conf_ext)
    discord_bot.extend(stats_ext)
    discord_bot.extend(ranking_ext)
    discord_bot.extend(invite_ext)

    # Start bot
    discord_bot.run()

    return 0

if __name__ == "__main__":
    res = main(sys.argv)
    exit(res)
