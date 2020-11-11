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

class InvalidConfigException(Exception):
    def __init__(self, msg: str, var_name: str):
        super().__init__(f'{msg}, check {var_name} value in .env file')

class NotCoroutineException(TypeError):
    def __init__(self, func):
        super().__init__(f'{str(func)} is not a coroutine function')

class MissingResourceException(Exception):
    def __init__(self, xml: str, path: str):
        super().__init__(f'Missing resource in {xml}: {path}')