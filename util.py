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

import importlib
import json
import os.path
import asyncio
import shlex
import discord

CONFIG_SCHEMA_PATH = "config_schema.json"

#################
# Utility Funcs #
#################

def write_file(path: str, content: str):
    with open(path, "w") as f:
        f.write(content)

def default_by_schema(schema: dict):
    if "default" in schema:
        return schema["default"]
    if "properties" not in schema:
        return None
    res = {}
    schemas = schema["properties"]
    for key in schemas:
        res[key] = default_by_schema(schemas[key])
    return res

def type_str(o):
    return str(type(o)).split('\'')[1]

py_to_json_type = {
    'dict':     'object',
    'list':     'array',
    'tuple':    'array',
    'str':      'string',
    'int':      'integer',
    'float':    'double',
    'bool':     'boolean',
    'NoneType': 'null',
}

json_to_py_type = {
    'object':   'dict',
    'array':    'list',
    'string':   'str',
    'double':   'float',
    'integer':  'int',
    'boolean':  'bool',
    'null':     'NoneType',
}

def json_type_str(o):
    return py_to_json_type[type_str(o)]

def check_with_schema(schema: dict, v):
    if json_type_str(v) != schema["type"]:
        t = schema["type"]
        raise TypeError(f"Wrong type '{type_str(v)}', expected '{t}'")
    if "properties" not in schema:
        return
    schemas = schema["properties"]
    for key in v:
        if key not in schemas:
            raise KeyError(f"Unexpected key '{key}'")
        check_with_schema(schemas[key], v[key])

__module_cache = {}
def get_module_element(path: str):
    splited_path = path.split('.')
    module_name = '.'.join(splited_path[:-1])
    object_name = splited_path[-1]
    if module_name not in __module_cache:
        __module_cache[module_name] = importlib.import_module(module_name)
    module = __module_cache[module_name]
    return getattr(module, object_name)

def parse_control_message(prefix: str, message: discord.Message):
        prefix_len = len(prefix)
        msg = message.content.strip()

        msg_prefix = msg[: prefix_len]
        msg_suffix = msg[prefix_len :]

        if msg_prefix != prefix or msg_suffix == "":
            return None

        return shlex.split(msg_suffix)

def check_coroutine(func):
    if not asyncio.iscoroutinefunction(func):
        raise NotCoroutineException(func)

def build_cmdcoro_usage(prefix: str, cmdname, func):
    f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    assert len(f_args) >= 2
    f_args = f_args[2:]
    args_str = ' ' + ' '.join(["{%s}" % arg for arg in f_args])
    return f'{prefix}{cmdname}' + args_str

def cmdcoro(func):
    check_coroutine(func)

    f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
    assert len(f_args) >= 2
    f_args = f_args[2:]

    async def wrapped_func(client, message, argv):
        if len(f_args) != len(argv) - 1:
            usage_str = 'Usage: ' + build_cmdcoro_usage(argv[0], func)
            await message.channel.send(usage_str)
        else:
            await func(client, message, *argv[1:])

    setattr(wrapped_func, "or_cmdcoro", func)
    
    return wrapped_func

###########################
# Bot model utility funcs #
###########################

def is_user_member(user: discord.User):
    return isinstance(user, discord.Member)

def qualified_name(user: discord.User):
    return f'{user.name}#{user.discriminator}'

def get_channel_env_var_name(n):
    return f'DISCORD_CHANNEL_{n}'

def get_channel_id(n):
    var_name = get_channel_env_var_name(n)
    try:
        res = os.environ.get(var_name)
        return int(res) if res is not None else None
    except ValueError as e:
        raise InvalidConfigException(str(e), var_name)

def is_text_channel(channel):
    return channel.type == discord.ChannelType.text

def is_dm_message(message: discord.Message):
    return isinstance(message.channel, discord.DMChannel)

def is_same_author(m1: discord.Message, m2: discord.Message):
    return m1.author.id == m2.author.id


#################
# DB Converters #
#################

def role_to_row(role: discord.Role):
    return {
        'did': role.id,
        'name': role.name,
        'created_at': role.created_at
    }

def roles_to_rows(roles: list):
    rows = [role_to_row(r) for r in roles]
    rows = sorted(rows, key = lambda i: i['did'])
    for i in range(len(rows)):
        rows[i]['idx'] = i
    return rows

def role_mask(user: discord.Member, role_map: dict):
    mask = ['0'] * len(role_map)
    for role in user.roles:
        idx = role_map[role.id]['idx']
        mask[idx] = '1'
    return ''.join(mask)

def user_to_row(user: discord.User, role_map: dict):
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': None,
        'roles': '0' * len(role_map)
    }

def member_to_row(user: discord.Member, role_map: dict):
    return {
        'did': user.id,
        'name': user.name,
        'disc': user.discriminator,
        'display_name': user.display_name,
        'roles': role_mask(user, role_map)
    }

def new_message_to_row(msg: discord.Message, event_id: int):
    return {
        'type_id': event_id,
        'user_id': msg.author.id,
        'author_id': msg.author.id,
        'message_id': msg.id,
        'channel_id': msg.channel.id,
        'created_at': msg.created_at
    }

###################
# Utility Classes #
###################

class InvalidConfigException(Exception):
    def __init__(self, msg: str, var_name: str):
        super().__init__(f'{msg}, check {var_name} value in .env file')

class NotCoroutineException(TypeError):
    def __init__(self, func):
        super().__init__(f'{str(func)} is not a coroutine function')

class ConfigView(object):

    schema = None

    def __init__(self, *args, **kwargs):
        if len(args) == 1 or 'config_path' in kwargs:
            self.__load_from_file(*args, **kwargs)
        else:
            self.__construct(*args, **kwargs)

    def __construct(self, schema: dict, config, default_config):
        self.schema = schema
        self.config = config
        self.default_config = default_config

    def __load_from_file(self, config_path: str):
        with open(CONFIG_SCHEMA_PATH, "r") as f:
            self.schema = json.load(f)

        self.default_config = default_by_schema(self.schema)

        if not os.path.exists(config_path):
            # if config not exist dump default
            with open(config_path, "w") as f:
                json.dump(self.default_config, f)
            self.config = self.default_config
        else:
            # if config do exist load it
            with open(config_path, "r") as f:
                self.config = json.load(f)
            check_with_schema(self.schema, self.config)

    def contains(self, path: str):
        keys = path.split('.')
        node = self.default_config
        for el in keys:
            if el not in node:
                return False
            node = node[el]
        return True

    def path(self, path: str):
        keys = path.split('.')
        node = self.config
        default_node = self.default_config
        schema_node = self.schema
        found = True
        for el in keys:
            if el not in default_node:
                raise KeyError(f"No such path '{path}' in config schema")
            elif found and el in node:
                node = node[el]
            else:
                found = False
            default_node = default_node[el]
            schema_node = schema_node["properties"][el]
        node = node if found else default_node
        return ConfigView(schema_node, node, default_node)

    def get(self, path: str):
        return self.path(path).config

    def __bool__(self):
        return self.config.__bool__()

    def __getitem__(self, path):
        return self.get(path)

    def __setitem__(self, path, item):
        keys = path.split('.')
        node = self.config
        for el in keys[:-1]:
            if el not in node:
                node[el] = {}
            node = node[el]
        node[keys[-1]] = item
        check_with_schema(self.schema, self.config)
        return self.get(path)

    def __getattr__(self, key):
        return self.path(key)
