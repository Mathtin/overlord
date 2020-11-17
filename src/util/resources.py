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

import os.path
import xml.etree.ElementTree as ET
import logging
from .exceptions import MissingResourceException

log = logging.getLogger('util-resources')

def res_path(local_path: str):
    res_path = os.getenv('RESOURCE_PATH')
    return os.path.join(res_path, local_path)

def __xml_path(path: str):
    splited_path = path.split('.')
    xml_name = splited_path[0]
    return res_path(f'{xml_name}.xml')

def __string_path(path: str):
    splited_path = path.split('.')
    string_name = splited_path[1]
    return f'./string[@name="{string_name}"]'

__xml_cache = {}
def __get_node(xml_path: str, string_path: str):
    # Load xml
    if xml_path not in __xml_cache:
        if not os.path.isfile(xml_path):
            raise MissingResourceException(xml_path, string_path)
        log.info(f'Loading {xml_path}')
        __xml_cache[xml_path] = ET.parse(xml_path)
    root = __xml_cache[xml_path].getroot()
    # Find value
    return root.find(string_path)

def get(path: str):
    xml_path = __xml_path(path)
    string_path = __string_path(path)
    node = __get_node(xml_path, string_path)
    if node is None:
        return path
    return node.text
