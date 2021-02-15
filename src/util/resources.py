#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MIT License

Copyright (c) 2020-present Daniel [Mathtin] Shiko <wdaniil@mail.ru>
Project: Overlord discord bot
Contributors: Danila [DeadBlasoul] Popov <dead.blasoul@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__author__ = "Mathtin"

import os.path
from typing import Dict
import xml.etree.ElementTree as ET
import logging
from .exceptions import MissingResourceException

log = logging.getLogger('util-resources')


def res_path(local_path: str):
    path = os.getenv('RESOURCE_PATH')
    return os.path.join(path, local_path)


STRING_RESOURCE_FILE = 'strings.xml'


class StringResourceView(object):

    _strings_path: str
    _lang: str
    _root: ET.Element
    _path_cache: Dict[str, str]

    def __init__(self, lang: str = 'en') -> None:
        self._strings_path = res_path(STRING_RESOURCE_FILE)
        if not os.path.isfile(self._strings_path):
            raise MissingResourceException(self._strings_path, STRING_RESOURCE_FILE)
        log.info(f'Loading {self._strings_path}')
        self._root = ET.parse(self._strings_path).getroot()
        self.switch_lang(lang)

    @staticmethod
    def _section_name(section: str) -> str:
        res = section.lower()
        if not res.endswith('s'):
            res += 's'
        return res

    @staticmethod
    def _attribute_name(attrib: str) -> str:
        return attrib.lower().replace('_', '-')

    def switch_lang(self, lang: str):
        self._lang = lang
        self._path_cache = {}

    def get(self, path: str) -> str:
        if path in self._path_cache:
            return self._path_cache[path]
        [section, type_, name] = path.split('.')
        section = StringResourceView._section_name(section)
        type_ = StringResourceView._attribute_name(type_)
        name = StringResourceView._attribute_name(name)
        res = self._root.find(f'.//{section}/string[@lang="{self._lang}"][@type="{type_}"][@name="{name}"]')
        self._path_cache[path] = res.text if res is not None else path
        return self._path_cache[path]

    class TypeView(object):

        def __init__(self, section, type_: str) -> None:
            self.section = section
            self.type = type_

        def __getattr__(self, name: str) -> str:
            return self.section.view.get(f'{self.section.section}.{self.type}.{name}')

    class SectionView(object):

        def __init__(self, view, section: str) -> None:
            self.view = view
            self.section = section

        def __getattr__(self, name: str):
            return StringResourceView.TypeView(self, name)

    def __getattr__(self, name: str):
        return StringResourceView.SectionView(self, name)


R = StringResourceView()
