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

import logging.config

from .config import ConfigView

#################
# Logger Config #
#################

class LogFileConfig(object):
    """
    file {
        filename = "..."
        maxBytes = ...
        backupCount = ...
    }
    """
    filename : str = "overlord-bot.log"
    maxBytes : int = 1048576
    backupCount : int = 10

class DiscordLogConfig(object):
    """
    discord {
        channel = ...
    }
    """
    channel : int = 0

class LoggerRootConfig(object):
    """
    logger {
        format = "..."
        level = "..."
        file : LogFileConfig
        discord : DiscordLogConfig
    }
    """
    format  : str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    level   : str              = "INFO"
    file    : LogFileConfig    = LogFileConfig()
    discord : DiscordLogConfig = DiscordLogConfig()

def update_config(config: LoggerRootConfig) -> None:
    config_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": config.format
            }
        },
        "handlers": {
            "console": {
                "level": config.level,
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr"
            },
            "file": {
                "level": config.level,
                "formatter": "standard",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": config.file.filename,
                "maxBytes": config.file.maxBytes,
                "backupCount": config.file.backupCount
            }
        },
        "root": {
            "handlers": [
                "console",
                "file"
            ],
            "level": config.level
        }
    }
    logging.config.dictConfig(config_dict)
