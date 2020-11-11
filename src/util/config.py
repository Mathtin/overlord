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
import os.path

from .resources import res_path

CONFIG_SCHEMA_FILE = "config_schema.json"

PY_TO_JSON_TYPE = {
    'dict':     'object',
    'list':     'array',
    'tuple':    'array',
    'str':      'string',
    'int':      'integer',
    'float':    'double',
    'bool':     'boolean',
    'NoneType': 'null',
}

JSON_TO_PY_TYPE = {
    'object':   'dict',
    'array':    'list',
    'string':   'str',
    'double':   'float',
    'integer':  'int',
    'boolean':  'bool',
    'null':     'NoneType',
}

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

def json_type_str(o):
    return PY_TO_JSON_TYPE[type_str(o)]

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
        config_schema_path = res_path(CONFIG_SCHEMA_FILE)
        with open(config_schema_path, "r") as f:
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
