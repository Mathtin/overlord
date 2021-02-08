#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###################################################
#........../\./\...___......|\.|..../...\.........#
#........./..|..\/\.|.|_|._.|.\|....|.c.|.........#
#......../....../--\|.|.|.|i|..|....\.../.........#
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
import json
from util.config.manager import ConfigManager
from util.exceptions import InvalidConfigException

from util.extbot import embed_long_message
from .base import BotExtension
from util import ConfigView, code_msg, send_long_message
import util.resources as res

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

    @BotExtension.command("reload_config", desciption="Reload config from disk")
    async def cmd_reload_config(self, msg: discord.Message):
        log.info(f'Reloading config')
        # Reload config
        await self.bot.reload_config()
        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))

    @BotExtension.command("save_config", desciption="Save config on disk")
    async def cmd_save_config(self, msg: discord.Message):
        log.info(f'Saving config')
        self.bot.save_config()
        log.info(f'Done')
        await msg.channel.send(res.get("messages.done"))

    @BotExtension.command("get_config_value", desciption="Print config value (in json)")
    async def cmd_get_config_value(self, msg: discord.Message, path: str):
        embed = self.bot.base_embed("Overlord Configuration", f"⚙ {path} value", '', self.__color__)
        try:
            value = self.get_raw(path)
            value_s = code_msg(value)
            embed_long_message(embed, value_s)
            await msg.channel.send(embed=embed)
        except KeyError:
            await msg.channel.send(res.get("messages.invalid_config_path"))

    @BotExtension.command("alter_config", desciption="Set config value (in json, use quote to wrap complex values)")
    async def cmd_alter_config(self, msg: discord.Message, path: str, value: str):
        old_config = self.raw_config
        try:
            self.set_raw(path, value)
        except KeyError:
            self.set_raw('.', old_config)
            await msg.channel.send(res.get("messages.invalid_config_path"))
            return
        except InvalidConfigException as e:
            self.set_raw('.', old_config)
            log.info(f'Invalid config value provided: {e}')
            await msg.channel.send(res.get("messages.invalid_config_value").format(str(e)))
            return
        # Update config properly
        err = await self.bot.safe_update_config()
        if not err:
            answer = res.get("messages.done")
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
        await msg.channel.send(answer)

