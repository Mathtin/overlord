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
import copy

from discord.errors import InvalidArgument

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

    __schema: dict
    __fpath: str

    __value = None
    __default_value = None
    __parent = None

    def __init__(self, **kwargs):

        self.__fpath = None
        self.__schema = None

        if 'fpath' in kwargs:
            self.__fpath = kwargs['fpath']
            del kwargs['fpath']
        if 'parent' in kwargs:
            self.__parent = kwargs['parent']
            del kwargs['parent']

        if 'path' in kwargs and 'schema_name' in kwargs:
            self.__construct3(**kwargs)
        elif 'value' in kwargs and 'schema_name' in kwargs:
            self.__construct2(**kwargs)
        elif 'value' in kwargs and 'schema' in kwargs:
            self.__construct1(**kwargs)
        else:
            raise InvalidArgument("Bad kwargs")

    def __construct1(self, schema: dict, value):
        self.__schema = schema
        self.__value = value
        self.__default_value = default_by_schema(self.__schema)
        check_with_schema(self.__schema, self.__value)

    def __construct2(self, schema_name: str, value):
        config_schema_path = res_path(f'{schema_name}.json')
        with open(config_schema_path, "r") as f:
            schema = json.load(f)
        self.__construct1(schema, value)

    def __construct3(self, schema_name: str, path: str):
        self.__fpath = path
        if not os.path.exists(path):
            # if config not exist dump default
            with open(path, "w") as f:
                json.dump(self.__default_value, f, indent=4)
            value = self.__default_value
        else:
            # if config do exist load it
            with open(path, "r") as f:
                value = json.load(f)
        self.__construct2(schema_name, value)

    def contains(self, path: str):
        keys = path.split('.')
        node = self.__default_value
        for el in keys:
            if el not in node:
                return False
            node = node[el]
        return True

    def path(self, path: str, schema_name=None):
        if path == '.':
            return self
        keys = path.split('.')
        node = self.__value
        default_node = self.__default_value
        schema_node = self.__schema
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
        res = ConfigView(schema=schema_node, value=node, fpath=self.fpath(), parent=self.parent())
        if schema_name is not None:
            res = res.with_schema(schema_name)
        return res

    def alter(self, path: str, value):
        if path == '.':
            self.__construct1(self.__schema, value)
            return
        keys = path.split('.')
        last_key = keys[-1]
        keys = keys[:-1]
        node = self.__value
        default_node = self.__default_value
        schema_node = self.__schema
        for el in keys:
            if el not in default_node:
                raise KeyError(f"No such path '{path}' in config schema")
            elif el not in node:
                node[el] = copy.deepcopy(default_node[el])
            node = node[el]
            default_node = default_node[el]
            schema_node = schema_node["properties"][el]
        node[last_key] = value
        self.__construct1(self.__schema, self.__value)

    def get(self, path: str):
        return self.path(path).__value

    def parent(self):
        return self.__parent if self.__parent is not None else self

    def schema(self):
        return self.__schema

    def fpath(self):
        return self.__fpath

    def value(self):
        return self.__value

    def copy(self):
        schema = copy.deepcopy(self.__schema)
        value = copy.deepcopy(self.__value)
        return ConfigView(schema=schema, value=value, fpath=self.__fpath, parent=self.__parent)

    def with_schema(self, schema_name: str):
        return ConfigView(schema_name=schema_name, value=copy.deepcopy(self.__value), fpath=self.__fpath, parent=self.__parent)

    def __bool__(self):
        return bool(self.__value)

    def __getitem__(self, path):
        return self.get(path)

    def __setitem__(self, path, item):
        keys = path.split('.')
        node = self.__value
        for el in keys[:-1]:
            if el not in node:
                node[el] = {}
            node = node[el]
        node[keys[-1]] = item
        check_with_schema(self.__schema, self.__value)
        return self.get(path)

    def __getattr__(self, key):
        return self.path(key)

    def __iter__(self):
        return self.__default_value.__iter__()
