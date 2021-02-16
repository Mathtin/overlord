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
from .exceptions import MissingResourceException


def res_path(local_path: str):
    path = os.getenv('RESOURCE_PATH')
    return os.path.join(path, local_path)


class XStrings(object):
    class XName(object):
        class XCommon(object):
            _type_name = "common"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def TRACEBACK(self) -> str:
                return self._section.get(self._type_name, "traceback")
        
            @property
            def EXTENSION(self) -> str:
                return self._section.get(self._type_name, "extension")
        
            @property
            def GUILD(self) -> str:
                return self._section.get(self._type_name, "guild")
        
            @property
            def CHANNEL(self) -> str:
                return self._section.get(self._type_name, "channel")
        
            @property
            def ERROR(self) -> str:
                return self._section.get(self._type_name, "error")
        
            @property
            def INFO(self) -> str:
                return self._section.get(self._type_name, "info")
        
            @property
            def LOG_CHANNEL(self) -> str:
                return self._section.get(self._type_name, "log-channel")
        
            @property
            def CONTROL_CHANNEL(self) -> str:
                return self._section.get(self._type_name, "control-channel")
        
            @property
            def MAINTAINER(self) -> str:
                return self._section.get(self._type_name, "maintainer")
        
    
        class XUserStat(object):
            _type_name = "user-stat"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def MEMBERSHIP(self) -> str:
                return self._section.get(self._type_name, "membership")
        
            @property
            def NEW_MESSAGE_COUNT(self) -> str:
                return self._section.get(self._type_name, "new-message-count")
        
            @property
            def DELETE_MESSAGE_COUNT(self) -> str:
                return self._section.get(self._type_name, "delete-message-count")
        
            @property
            def EDIT_MESSAGE_COUNT(self) -> str:
                return self._section.get(self._type_name, "edit-message-count")
        
            @property
            def NEW_REACTION_COUNT(self) -> str:
                return self._section.get(self._type_name, "new-reaction-count")
        
            @property
            def DELETE_REACTION_COUNT(self) -> str:
                return self._section.get(self._type_name, "delete-reaction-count")
        
            @property
            def VC_TIME(self) -> str:
                return self._section.get(self._type_name, "vc-time")
        
            @property
            def MIN_WEIGHT(self) -> str:
                return self._section.get(self._type_name, "min-weight")
        
            @property
            def MAX_WEIGHT(self) -> str:
                return self._section.get(self._type_name, "max-weight")
        
            @property
            def EXACT_WEIGHT(self) -> str:
                return self._section.get(self._type_name, "exact-weight")
        
    
        _section_name = "names"
        COMMON: XCommon
        USER_STAT: XUserStat
    
        def __init__(self, res) -> None:
            self._res = res
            self.COMMON = XStrings.XName.XCommon(self)
            self.USER_STAT = XStrings.XName.XUserStat(self)
    
        def get(self, type_name, string_name) -> str:
            return self._res.get(self._section_name, type_name, string_name)

    class XEmbed(object):
        class XHeader(object):
            _type_name = "header"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def DEFAULT(self) -> str:
                return self._section.get(self._type_name, "default")
        
            @property
            def ERROR_REPORT(self) -> str:
                return self._section.get(self._type_name, "error-report")
        
            @property
            def WARN_REPORT(self) -> str:
                return self._section.get(self._type_name, "warn-report")
        
            @property
            def INFO_REPORT(self) -> str:
                return self._section.get(self._type_name, "info-report")
        
            @property
            def LOG_REPORT(self) -> str:
                return self._section.get(self._type_name, "log-report")
        
    
        class XFooter(object):
            _type_name = "footer"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def DEFAULT(self) -> str:
                return self._section.get(self._type_name, "default")
        
    
        class XTitle(object):
            _type_name = "title"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def SUCCESS(self) -> str:
                return self._section.get(self._type_name, "success")
        
            @property
            def ERROR(self) -> str:
                return self._section.get(self._type_name, "error")
        
            @property
            def WARNING(self) -> str:
                return self._section.get(self._type_name, "warning")
        
            @property
            def INFO(self) -> str:
                return self._section.get(self._type_name, "info")
        
            @property
            def TRACEBACK(self) -> str:
                return self._section.get(self._type_name, "traceback")
        
            @property
            def SUMMARY(self) -> str:
                return self._section.get(self._type_name, "summary")
        
            @property
            def CALL_ARGS(self) -> str:
                return self._section.get(self._type_name, "call-args")
        
            @property
            def COMMANDS_LIST(self) -> str:
                return self._section.get(self._type_name, "commands-list")
        
            @property
            def STAT_TYPE_LIST(self) -> str:
                return self._section.get(self._type_name, "stat-type-list")
        
            @property
            def STATS_LIST(self) -> str:
                return self._section.get(self._type_name, "stats-list")
        
            @property
            def RANK_TABLE(self) -> str:
                return self._section.get(self._type_name, "rank-table")
        
            @property
            def CONFIG_VALUE(self) -> str:
                return self._section.get(self._type_name, "config-value")
        
            @property
            def EXTENSION_STATUS_LIST(self) -> str:
                return self._section.get(self._type_name, "extension-status-list")
        
    
        _section_name = "embeds"
        HEADER: XHeader
        FOOTER: XFooter
        TITLE: XTitle
    
        def __init__(self, res) -> None:
            self._res = res
            self.HEADER = XStrings.XEmbed.XHeader(self)
            self.FOOTER = XStrings.XEmbed.XFooter(self)
            self.TITLE = XStrings.XEmbed.XTitle(self)
    
        def get(self, type_name, string_name) -> str:
            return self._res.get(self._section_name, type_name, string_name)

    class XMessage(object):
        class XStatus(object):
            _type_name = "status"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def COMMITTING(self) -> str:
                return self._section.get(self._type_name, "committing")
        
            @property
            def BUSY(self) -> str:
                return self._section.get(self._type_name, "busy")
        
            @property
            def PING(self) -> str:
                return self._section.get(self._type_name, "ping")
        
            @property
            def SYNC_USERS(self) -> str:
                return self._section.get(self._type_name, "sync-users")
        
            @property
            def UPDATING_RANKS(self) -> str:
                return self._section.get(self._type_name, "updating-ranks")
        
            @property
            def UPDATING_RANK(self) -> str:
                return self._section.get(self._type_name, "updating-rank")
        
            @property
            def DB_CLEAR_CHANNEL(self) -> str:
                return self._section.get(self._type_name, "db-clear-channel")
        
            @property
            def DB_LOAD_CHANNEL(self) -> str:
                return self._section.get(self._type_name, "db-load-channel")
        
            @property
            def DB_DROP_TABLE(self) -> str:
                return self._section.get(self._type_name, "db-drop-table")
        
            @property
            def CLEAR_STATS(self) -> str:
                return self._section.get(self._type_name, "clear-stats")
        
            @property
            def CALC_STATS(self) -> str:
                return self._section.get(self._type_name, "calc-stats")
        
            @property
            def STOP_EXTENSION(self) -> str:
                return self._section.get(self._type_name, "stop-extension")
        
            @property
            def REPORTED_TO(self) -> str:
                return self._section.get(self._type_name, "reported-to")
        
            @property
            def STARTED(self) -> str:
                return self._section.get(self._type_name, "started")
        
            @property
            def SUCCESS(self) -> str:
                return self._section.get(self._type_name, "success")
        
    
        class XError(object):
            _type_name = "error"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def INTERNAL(self) -> str:
                return self._section.get(self._type_name, "internal")
        
            @property
            def NO_ACCESS(self) -> str:
                return self._section.get(self._type_name, "no-access")
        
            @property
            def INVALID_ARGUMENT(self) -> str:
                return self._section.get(self._type_name, "invalid-argument")
        
            @property
            def UNKNOWN_COMMAND(self) -> str:
                return self._section.get(self._type_name, "unknown-command")
        
    
        class XDError(object):
            _type_name = "d-error"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def UNKNOWN_USER(self) -> str:
                return self._section.get(self._type_name, "unknown-user")
        
            @property
            def INVALID_USER(self) -> str:
                return self._section.get(self._type_name, "invalid-user")
        
            @property
            def INVALID_USER_MENTION(self) -> str:
                return self._section.get(self._type_name, "invalid-user-mention")
        
            @property
            def UNKNOWN_MEMBER(self) -> str:
                return self._section.get(self._type_name, "unknown-member")
        
            @property
            def INVALID_MEMBER(self) -> str:
                return self._section.get(self._type_name, "invalid-member")
        
            @property
            def INVALID_MEMBER_MENTION(self) -> str:
                return self._section.get(self._type_name, "invalid-member-mention")
        
            @property
            def USER_NOT_MEMBER(self) -> str:
                return self._section.get(self._type_name, "user-not-member")
        
            @property
            def UNKNOWN_CHANNEL(self) -> str:
                return self._section.get(self._type_name, "unknown-channel")
        
            @property
            def INVALID_CHANNEL(self) -> str:
                return self._section.get(self._type_name, "invalid-channel")
        
            @property
            def CHANNEL_NOT_TEXT(self) -> str:
                return self._section.get(self._type_name, "channel-not-text")
        
            @property
            def CHANNEL_NOT_VOICE(self) -> str:
                return self._section.get(self._type_name, "channel-not-voice")
        
            @property
            def UNKNOWN_ROLE(self) -> str:
                return self._section.get(self._type_name, "unknown-role")
        
            @property
            def INVALID_ROLE(self) -> str:
                return self._section.get(self._type_name, "invalid-role")
        
    
        class XDbError(object):
            _type_name = "db-error"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def UNKNOWN_USER(self) -> str:
                return self._section.get(self._type_name, "unknown-user")
        
            @property
            def INVALID_USER(self) -> str:
                return self._section.get(self._type_name, "invalid-user")
        
    
        class XConfigError(object):
            _type_name = "config-error"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def INVALID_PATH(self) -> str:
                return self._section.get(self._type_name, "invalid-path")
        
            @property
            def PARSE_FAIL(self) -> str:
                return self._section.get(self._type_name, "parse-fail")
        
    
        class XErrorOther(object):
            _type_name = "error-other"
        
            def __init__(self, section) -> None:
                self._section = section
        
            @property
            def INVALID_RANK(self) -> str:
                return self._section.get(self._type_name, "invalid-rank")
        
            @property
            def UNKNOWN_RANK(self) -> str:
                return self._section.get(self._type_name, "unknown-rank")
        
            @property
            def DUPLICATE_RANK(self) -> str:
                return self._section.get(self._type_name, "duplicate-rank")
        
            @property
            def DUPLICATE_WEIGHT(self) -> str:
                return self._section.get(self._type_name, "duplicate-weight")
        
            @property
            def UNKNOWN_STAT(self) -> str:
                return self._section.get(self._type_name, "unknown-stat")
        
            @property
            def NEGATIVE_STAT_VALUE(self) -> str:
                return self._section.get(self._type_name, "negative-stat-value")
        
    
        _section_name = "messages"
        STATUS: XStatus
        ERROR: XError
        D_ERROR: XDError
        DB_ERROR: XDbError
        CONFIG_ERROR: XConfigError
        ERROR_OTHER: XErrorOther
    
        def __init__(self, res) -> None:
            self._res = res
            self.STATUS = XStrings.XMessage.XStatus(self)
            self.ERROR = XStrings.XMessage.XError(self)
            self.D_ERROR = XStrings.XMessage.XDError(self)
            self.DB_ERROR = XStrings.XMessage.XDbError(self)
            self.CONFIG_ERROR = XStrings.XMessage.XConfigError(self)
            self.ERROR_OTHER = XStrings.XMessage.XErrorOther(self)
    
        def get(self, type_name, string_name) -> str:
            return self._res.get(self._section_name, type_name, string_name)

    _lang: str
    _root: ET.Element
    _path_cache: Dict[str, str]
    NAME: XName
    EMBED: XEmbed
    MESSAGE: XMessage

    def __init__(self, lang: str = 'en') -> None:
        self._strings_path = res_path("strings.xml")
        if not os.path.isfile(self._strings_path):
            raise MissingResourceException(self._strings_path, "strings.xml")
        self._root = ET.parse(self._strings_path).getroot()
        self.NAME = XStrings.XName(self)
        self.EMBED = XStrings.XEmbed(self)
        self.MESSAGE = XStrings.XMessage(self)
        self.switch_lang(lang)

    def switch_lang(self, lang: str) -> None:
        self._lang = lang
        self._path_cache = {}

    def get(self, section_name, type_name, string_name) -> str:
        path = '.'.join([section_name, type_name, string_name])
        if path in self._path_cache:
            return self._path_cache[path]
        res = self._root.find(f'.//{section_name}/string[@lang="{self._lang}"][@type="{type_name}"][@name="{string_name}"]')
        self._path_cache[path] = res.text if res is not None else path
        return self._path_cache[path]


STRINGS = XStrings()
