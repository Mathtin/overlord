#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
# ........../\./\...___......|\.|..../...\.........#
# ........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
# ......../....../--\|.|.|.|i|..|....\.../.........#
#        Mathtin (c)                              #
###################################################
#   Project: Overlord discord bot                 #
#   Author: Daniel [Mathtin] Shiko                #
#   Copyright (c) 2020 <wdaniil@mail.ru>          #
#   This file is released under the MIT license.  #
###################################################

__author__ = 'Mathtin'

import logging

import discord

from src.util.resources import R
from src.util import code_msg
from src.util.exceptions import InvalidConfigException
from src.util.extbot import embed_long_message
from .base import BotExtension

log = logging.getLogger('config-extension')


####################
# Config Extension #
####################

class ConfigExtension(BotExtension):

    __extname__ = '⚙ Config Extension'
    __description__ = 'Raw config manipulation commands'
    __color__ = 0x23BC71

    @property
    def config(self):
        return self.bot.cnf_manager.config

    @property
    def raw_config(self):
        return self.bot.cnf_manager.raw

    @property
    def parser(self):
        return self.bot.cnf_manager.parser

    def get_raw(self, path: str) -> str:
        return self.bot.cnf_manager.get_raw(path)

    def set_raw(self, path: str, value: str) -> None:
        self.bot.cnf_manager.set_raw(path, value)

    ############
    # Commands #
    ############

    @BotExtension.command("reload_config", description="Reload config from disk")
    async def cmd_reload_config(self, msg: discord.Message):
        log.info(f'Reloading config')
        # Reload config
        await self.bot.reload_config()
        log.info(f'Done')
        await msg.channel.send(R.MESSAGE.STATUS.SUCCESS)

    @BotExtension.command("save_config", description="Save config on disk")
    async def cmd_save_config(self, msg: discord.Message):
        log.info(f'Saving config')
        self.bot.save_config()
        log.info(f'Done')
        await msg.channel.send(R.MESSAGE.STATUS.SUCCESS)

    @BotExtension.command("get_config_value", description="Print config value (in json)")
    async def cmd_get_config_value(self, msg: discord.Message, path: str):
        embed = self.bot.new_embed(f"⚙ {path} value", '', header="Overlord Configuration", color=self.__color__)
        try:
            value = self.get_raw(path)
            value_s = code_msg(value)
            embed_long_message(embed, value_s)
            await msg.channel.send(embed=embed)
        except KeyError:
            await msg.channel.send(R.MESSAGE.CONFIG_ERROR.INVALID_PATH)

    @BotExtension.command("alter_config", description="Set config value (in json, use quote to wrap complex values)")
    async def cmd_alter_config(self, msg: discord.Message, path: str, value: str):
        old_config = self.raw_config
        try:
            self.set_raw(path, value)
        except KeyError:
            self.set_raw('.', old_config)
            await msg.channel.send(R.MESSAGE.CONFIG_ERROR.INVALID_PATH)
            return
        except InvalidConfigException as e:
            self.set_raw('.', old_config)
            log.info(f'Invalid config value provided: {e}')
            embed = self.bot.new_error_report(R.MESSAGE.CONFIG_ERROR.PARSE_FAIL, str(e))
            await msg.channel.send(embed=embed)
            return
        # Update config properly
        err = await self.bot.safe_update_config()
        if not err:
            await msg.channel.send(R.MESSAGE.SUCCESS)
        else:
            details = str(err) + '\n' + 'Config reverted'
            embed = self.bot.new_error_report(err.__class__.__name__, details)
            await msg.channel.send(embed=embed)
