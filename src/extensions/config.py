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

import logging
import discord
import json
from .base import BotExtension
from util import ConfigView, quote_msg, send_long_message
import util.resources as res

log = logging.getLogger('config-extension')

##################
# Stat Extension #
##################

class ConfigExtension(BotExtension):

    __extname__ = 'Config Extension'
    __description__ = 'Raw config manipulation commands'
    __color__ = 0x23BC71
            
    ############
    # Commands #
    ############

    @BotExtension.command("reload_config", desciption="Reload config from disk")
    async def cmd_reload_config(self, msg: discord.Message):
        log.info(f'Reloading config')
        # Reload config
        parent_config = self.bot.config.parent()
        new_config = ConfigView(path=parent_config.fpath(), schema_name="config_schema")
        if new_config['logger']:
            logging.config.dictConfig(new_config['logger'])
        await self.bot.update_config(new_config.bot)
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
        parent_config = self.bot.config.parent()
        try:
            value = parent_config[path]
            value_s = quote_msg(json.dumps(value, indent=4))
            header = res.get("messages.config_value_header")
            await send_long_message(msg.channel, f'{header}\n{value_s}')
        except KeyError:
            await msg.channel.send(res.get("messages.invalid_config_path"))

    @BotExtension.command("alter_config", desciption="Set config value (in json, use quote to wrap complex values)")
    async def cmd_alter_config(self, msg: discord.Message, path: str, value: str):
        try:
            value_obj = json.loads(value)
        except json.decoder.JSONDecodeError:
            log.info(f'Invalid json value provided: {value}')
            await msg.channel.send(res.get("messages.invalid_json_value"))
            return

        try:
            err = await self.bot.safe_alter_config(path, value_obj)
        except KeyError as e:
            print(e)
            log.info(f'Invalid config path provided: {path}')
            await msg.channel.send(res.get("messages.invalid_config_path"))
            return False
        
        if not err:
            log.info(f'Done')
            await msg.channel.send(res.get("messages.done"))
        else:
            answer = res.get("messages.error").format(err) + '\n' + res.get("messages.warning").format('Config reverted')
            await msg.channel.send(answer)
