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

import json
import logging

import bot
import db

from util import *
import util.resources as res

log = logging.getLogger('control')

############################
# Control command Handlers #
############################


@cmdcoro
async def reload_config(client: bot.Overlord, msg: discord.Message):
    log.info(f'Reloading config')
    # Reload config
    parent_config = client.config.parent()
    new_config = ConfigView(path=parent_config.fpath(), schema_name="config_schema")
    if new_config['logger']:
        logging.config.dictConfig(new_config['logger'])
    client.update_config(new_config.bot)
    log.info(f'Done')
    await client.control_channel.send(res.get("messages.done"))

def __save_config(client: bot.Overlord):
    log.warn(f'Dumping raw config')
    parent_config = client.config.parent()
    with open(parent_config.fpath(), "w") as f:
        json.dump(parent_config.value(), f, indent=4)

@cmdcoro
async def save_config(client: bot.Overlord, msg: discord.Message):
    log.info(f'Saving config')
    __save_config(client)
    log.info(f'Done')
    await client.control_channel.send(res.get("messages.done"))

@cmdcoro
async def get_config_value(client: bot.Overlord, msg: discord.Message, path: str):
    parent_config = client.config.parent()
    try:
        value = parent_config[path]
        value_s = quote_msg(json.dumps(value, indent=4))
        header = res.get("messages.config_value_header")
        await client.control_channel.send(f'{header}\n{value_s}')
    except KeyError:
        await client.control_channel.send(res.get("messages.invalid_config_path"))

async def __safe_alter_config(client: bot.Overlord, path: str, value):
    parent_config = client.config.parent()

    try:
        old_value = parent_config[path]
    except KeyError:
        log.info(f'Invalid config path provided: {path}')
        await client.control_channel.send(res.get("messages.invalid_config_path"))
        return False

    try:
        log.warn(f'Altering raw config path {path}')
        parent_config.alter(path, value)
        if parent_config['logger']:
            logging.config.dictConfig(parent_config['logger'])
        client.update_config(parent_config.bot)
    except (InvalidConfigException, TypeError) as e:
        log.warn(f'Invalid config value provided: {value}, reason: {e}. Reverting.')
        parent_config.alter(path, old_value)
        if parent_config['logger']:
            logging.config.dictConfig(parent_config['logger'])
        client.update_config(parent_config.bot)
        msg = res.get("messages.error").format(e) + '\n' + res.get("messages.warning").format('Config reverted')
        await client.control_channel.send(msg)
        return False
    
    return True

@cmdcoro
async def alter_config(client: bot.Overlord, msg: discord.Message, path: str, value: str):
    try:
        value_obj = json.loads(value)
    except json.decoder.JSONDecodeError:
        log.info(f'Invalid json value provided: {value}')
        await client.control_channel.send(res.get("messages.invalid_json_value"))
        return

    if await __safe_alter_config(client, path, value_obj):
        log.info(f'Done')
        await client.control_channel.send(res.get("messages.done"))

