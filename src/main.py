#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2020-present Daniel [Mathtin] Shiko <wdaniil@mail.ru>
Project: Overlord discord bot
Contributors: Danila [DeadBlasoul] Popov <dead.blasoul@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__author__ = "Mathtin"

import os
import sys
import argparse

from dotenv import load_dotenv
load_dotenv()

from util import ConfigView, ConfigManager
from util.logger import LoggerRootConfig, update_config as update_logger
from db import DBPersistSession, EventType, UserStatType
from db.predefined import EVENT_TYPES, USER_STAT_TYPES
from overlord import OverlordRootConfig
from overlord.bot import Overlord
from extensions import UtilityExtension, RankingExtension, ConfigExtension, StatsExtension, InviteExtension
from extensions import RankingRootConfig, InviteRootConfig


class ExtensionsConfig(ConfigView):
    """
    extension {
        rank   : RankingRootConfig
        invite : InviteRootConfig
    }
    """
    rank: RankingRootConfig = RankingRootConfig()
    invite: InviteRootConfig = InviteRootConfig()


class RootConfig(ConfigView):
    """
    logger      : LoggerRootConfig
    bot         : OverlordRootConfig
    extension   : ExtensionsConfig
    """
    logger: LoggerRootConfig = LoggerRootConfig()
    bot: OverlordRootConfig = OverlordRootConfig()
    extension: ExtensionsConfig = ExtensionsConfig()


class Configuration(ConfigManager):
    config: RootConfig

    def alter(self, raw: str) -> None:
        super().alter(raw)
        update_logger(self.config.logger)


def main(argv):

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
    session = DBPersistSession(url)
    session.sync_table(EventType, 'name', EVENT_TYPES)
    session.sync_table(UserStatType, 'name', USER_STAT_TYPES)

    # Init bot
    discord_bot = Overlord(cnf_manager, session)

    # Init extensions
    extras_ext = UtilityExtension(bot=discord_bot)
    stats_ext = StatsExtension(bot=discord_bot)
    ranking_ext = RankingExtension(bot=discord_bot, priority=1)
    conf_ext = ConfigExtension(bot=discord_bot)
    # invite_ext = InviteExtension(bot=discord_bot)

    # Attach extensions
    discord_bot.extend(extras_ext)
    discord_bot.extend(conf_ext)
    discord_bot.extend(stats_ext)
    discord_bot.extend(ranking_ext)
    # discord_bot.extend(invite_ext)

    # Start bot
    discord_bot.run()

    return 0


if __name__ == "__main__":
    res = main(sys.argv)
    exit(res)
