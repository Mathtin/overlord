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

import typing

from .view import ConfigView
from .parser import ConfigParser
from typing import Any, Dict, Optional, Type, get_type_hints

class ConfigManager(object):

    path      : str
    raw       : str
    raw_dict  : dict
    config    : ConfigView
    parser    : ConfigParser
    model     = None

    __section_model_cache : Dict[Type[ConfigView], Dict[Type[ConfigView], str]] = {}

    def __init__(self, path : str, parser : ConfigParser = None) -> None:
        if parser is None:
            parser = ConfigParser()
        if self.model is None:
            self.__class__.model = get_type_hints(self.__class__)['config']
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

    def section_path(self, element : Type[ConfigView], source : Type[ConfigView]) -> Optional[str]:
        if source not in self.__section_model_cache:
            self.__section_model_cache[source] = {source:'.'}
        cache = self.__section_model_cache[source]
        if element in cache:
            return cache[element]
        res = None
        types = get_type_hints(source)
        for field, type_ in types.items():
            if field.startswith('_') or \
                isinstance(type_, typing._GenericAlias) or \
                not issubclass(type_, ConfigView):
                continue
            path = self.section_path(element, type_)
            if path is not None:
                res = f'{field}.{path}' if path != '.' else field
                break
        cache[element] = res
        return res

    def find_section(self, model : Type[ConfigView]) -> Any:
        path = self.section_path(model, self.config.__class__)
        return self.config.get(path)
        
