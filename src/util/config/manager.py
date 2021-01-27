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

from .view import ConfigView
from .parser import ConfigParser
from typing import Any, Dict, Type, get_type_hints

class ConfigManager(object):

    path      : str
    raw       : str
    raw_dict  : dict
    config    : ConfigView
    parser    : ConfigParser
    model     = None

    __section_model_cache : Dict[ConfigView, str]

    def __init__(self, path : str, parser : ConfigParser = None) -> None:
        if parser is None:
            parser = ConfigParser()
        if self.model is None:
            self.__class__.model = get_type_hints(self.__class__)['config']
        self.__section_model_cache = {}
        self.path = path
        self.parser = parser
        self.reload()

    def reload(self) -> None:
        with open(self.path, 'r') as f:
            raw = f.read()
        self.alter(raw)

    def save(self) -> None:
        with open(self.path, 'w') as f:
            f.write(self.raw)

    def alter(self, raw : str) -> None:
        self.raw = raw
        self.raw_dict = self.parser.parse(self.raw)
        self.config = self.model(self.raw_dict)

    def resolve_section_path(self, model : ConfigView) -> str:
        if isinstance(self.config, model):
            return '.'
        return ''

    def find_section(self, model : Type[ConfigView]) -> Any:
        if model not in self.__section_model_cache:
            self.__section_model_cache[model] = self.resolve_section_path(model)
        path = self.__section_model_cache[model]
        return self.config.get(path)
        
