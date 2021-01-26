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

import os

import lark
from util.exceptions import InvalidConfigException
from util.resources import res_path
from lark import Lark, Transformer

class TreeToDict(Transformer):

    list = list
    assignment = tuple
    root = dict

    true = lambda self, _: True
    false = lambda self, _: False

    def section(self, s) -> str:
        return (s[0], dict(s[1:]))

    def name(self, s) -> str:
        (s,) = s
        return str(s)

    def string(self, s) -> str:
        (s,) = s
        return s[1:-1]

    def integer(self, n) -> int:
        (n,) = n
        return int(n)

    def float(self, n) -> float:
        (n,) = n
        return float(n)

class ConfigParser(object):

    __grammar: str
    __parser: Lark

    def __init__(self, grammar_file='config_grammar.lark', start='root') -> None:
        with open(res_path(grammar_file), 'r') as f:
            self.__grammar = f.read()
        self.__parser = Lark(self.__grammar, start=start, parser='lalr', transformer=TreeToDict())
        
    @property
    def grammar(self) -> str:
        return self.__grammar

    def parse(self, data: str) -> dict:
        try:
            return self.__parser.parse(data)
        except lark.exceptions.UnexpectedToken as e:
            raise InvalidConfigException(str(e), "root")
