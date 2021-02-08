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

import os.path
from typing import Dict
import xml.etree.ElementTree as ET
import logging
from .exceptions import MissingResourceException

log = logging.getLogger('util-resources')


def res_path(local_path: str):
    res_path = os.getenv('RESOURCE_PATH')
    return os.path.join(res_path, local_path)
    

STRING_RESOURCE_FILE = 'strings.xml'

class StringResourceView(object):

    _strings_path:  str
    _lang:          str
    _root:          ET.Element
    _path_cache:   Dict[str, str]

    def __init__(self, lang='en') -> None:
        self._lang = lang
        self._strings_path = res_path(STRING_RESOURCE_FILE)
        if not os.path.isfile(self._strings_path):
            raise MissingResourceException(self._strings_path, STRING_RESOURCE_FILE)
        log.info(f'Loading {self._strings_path}')
        self._root = ET.parse(self._strings_path).getroot()
        self._path_cache = {}

    @staticmethod
    def _section_name(section: str) -> str:
        res = section.lower()
        if not res.endswith('s'):
            res += 's'
        return res

    @staticmethod
    def _attribute_name(attrib: str) -> str:
        return attrib.lower().replace('_','-')

    def get(self, path: str) -> str:
        if path in self._path_cache:
            return self._path_cache[path]
        [section, type_, name] = path.split('.')
        section = StringResourceView._section_name(section)
        type_ = StringResourceView._attribute_name(type_)
        name = StringResourceView._attribute_name(name)
        res = self._root.find(f'./{section}/string[@lang="{self._lang}" and @type="{type_}" and @name="{name}"]')
        self._path_cache[path] = res.text if res is not None else path
        return self._path_cache[path]

    class TypeView(object):

        def __init__(self, section, type: str) -> None:
            self._section = section
            self._type = type

        def __getattr__(self, name: str):
            return self._section._view.get(f'{self._section._section}.{self._type}.{name}')

    class SectionView(object):

        def __init__(self, view, section: str) -> None:
            self._view = view
            self._section = section

        def __getattr__(self, name: str):
            return StringResourceView.TypeView(self, name)
    
    def __getattr__(self, name: str):
        return StringResourceView.SectionView(self, name)


R = StringResourceView()
def set_language(lang: str):
    global R
    R = StringResourceView(lang)