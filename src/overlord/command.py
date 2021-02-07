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

from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, get_type_hints

import db as DB
import discord as DIS
import util.resources as res

from discord.errors import InvalidArgument

from util import check_coroutine
from .types import OverlordMember

_type_arg_converter_map: Dict[Type[Any], Callable[[DIS.Message, Any, str], Awaitable[Optional[str]]]] = {}
class OverlordCommand(object):

    optional_prefix = 'opt_'
    
    func:       Callable[..., Awaitable[None]]
    name:       str
    desciption: str
    req_f_args: List[str]
    f_args:     List[str]
    hints:      Dict[str, Type[Any]]
    args_str:   str

    def __init__(self, func, name: str, desciption='') -> None:
        super().__init__()
        check_coroutine(func)
        self.func = func
        self.name = name
        self.desciption = desciption
        f_args = func.__code__.co_varnames[:func.__code__.co_argcount]
        assert len(f_args) >= 2
        self.f_args = f_args[2:]
        self.hints = {k:v for k,v in get_type_hints(func).items() if k in self.f_args}
        self.req_f_args = []
        args = []
        optionals = False
        for a in self.f_args:
            arg = a
            if a in self.hints:
                arg += f': {self.hints[a].__name__}'
            if not a.lower().startswith(self.optional_prefix):
                self.req_f_args.append(a)
                args.append(f'{{{arg}}}')
            elif optionals:
                raise InvalidArgument(f'Non-optional argument {a} found after optinal argument in {name} command coroutine')
            else:
                optionals = True
                args.append(f'[{arg[len(self.optional_prefix):]}]')
        self.args_str = ' '.join(args)

    def usage(self, prefix: str, cmdname: str) -> str:
        return f'{prefix}{cmdname} {self.args_str}'

    def help(self, prefix: str, aliases: List[str]) -> str:
        if not aliases:
            return 'This command is disabled. Please, add appropriate config'
        usage_line = f'Usage: `{prefix}{aliases[0]} {self.args_str}`' if self.args_str \
            else f'Usage: `{prefix}{aliases[0]}`'
        desciption_line = f'{self.desciption}'
        aliases_str = ' ,'.join([f'`{prefix}{a}`' for a in aliases[1:]])
        aliases_line = f'Aliases: {aliases_str}'
        return '\n'.join([usage_line, desciption_line, aliases_line])

    def handler(self, ext):
        async def wrapped_func(message: DIS.Message, prefix: str, argv: List[str]):
            cmd = argv[0]
            argv = argv[1:]
            if len(self.req_f_args) > len(argv) or len(argv) > len(self.f_args):
                usage_str = 'Usage: ' + self.usage(prefix, cmd)
                await message.channel.send(usage_str)
                return
            argv = await self._convert_argv(message, ext, argv)
            if argv is None:
                usage_str = 'Usage: ' + self.usage(prefix, cmd)
                await message.channel.send(usage_str)
                return
            try:
                await self.func(ext, message, *argv)
            except:
                await ext.on_error(self.func.__name__, message, prefix, argv)
        return wrapped_func

    async def _convert_argv(self, msg: DIS.Message, ext: Any, argv: List[str]) -> Optional[List[Any]]:
        res = [a for a in argv]
        for i in range(len(res)):
            name = self.f_args[i]
            if name in self.hints:
                arg = await self._convert_arg(msg, ext, name, res[i], self.hints[name])
                if arg is None:
                    return None
                res[i] = arg
        return res

    @staticmethod
    async def _convert_arg(msg: DIS.Message, ext: Any, name: str, arg: str, type_: Type[Any]) -> Optional[Any]:
        if type_ in _type_arg_converter_map:
            return await _type_arg_converter_map[type_](msg, ext, arg)
        try:
            return type_(arg)
        except ValueError:
            await msg.channel.send(res.get("messages.invalid_command_arg").format(name, type_.__name__))

    class _for_type(object):
        def __init__(self, type_) -> None:
            self.type = type_
        def __call__(self, func: Callable[..., Any]):
            _type_arg_converter_map[self.type] = func
            return func

    @staticmethod
    @_for_type(DB.User)
    async def _resolve_db_user_w_fb(fb: DIS.Message, ext: Any, user_mention: str) -> Optional[DB.User]:
        user = await ext.bot.resolve_user(user_mention)
        if user is None:
            await fb.channel.send(res.get("messages.unknown_user"))
            return None
        return user

    @staticmethod
    @_for_type(DIS.User)
    async def _resolve_user_w_fb(fb: DIS.Message, ext: Any, user_mention: str) -> Optional[DIS.User]:
        user = await ext.bot.resolve_user(user_mention)
        if user is None:
            await fb.channel.send(res.get("messages.unknown_user"))
            return None
        try:
            d_user = await ext.bot.fetch_user(user.id)
        except DIS.NotFound:
            await fb.channel.send(res.get("messages.unknown_user"))
            return None
        return d_user

    @staticmethod
    @_for_type(DIS.Member)
    async def _resolve_member_w_fb(fb: DIS.Message, ext: Any, user_mention: str) -> Optional[DIS.Member]:
        user = await ext.bot.resolve_user(user_mention)
        if user is None:
            await fb.channel.send(res.get("messages.unknown_user"))
            return None
        try:
            member = await ext.bot.guild.fetch_member(user.id)
        except DIS.NotFound:
            await fb.channel.send(res.get("messages.not_member_user"))
            return None
        return member

    @staticmethod
    @_for_type(DIS.TextChannel)
    async def _resolve_text_channel_w_fb(fb: DIS.Message, ext: Any, channel_mention: str) -> Optional[DIS.TextChannel]:
        channel = await ext.bot.resolve_text_channel(channel_mention)
        if channel is None:
            if await ext.bot.resolve_voice_channel(channel_mention) is not None:
                await fb.channel.send(res.get("messages.invalid_channel_type_text"))
            else:
                await fb.channel.send(res.get("messages.unknown_channel"))
            return None
        return channel

    @staticmethod
    @_for_type(DIS.VoiceChannel)
    async def _resolve_voice_channel_w_fb(fb: DIS.Message, ext: Any, channel_mention: str) -> Optional[DIS.VoiceChannel]:
        channel = await ext.bot.resolve_voice_channel(channel_mention)
        if channel is None:
            if await ext.bot.resolve_text_channel(channel_mention) is not None:
                await fb.channel.send(res.get("messages.invalid_channel_type_voice"))
            else:
                await fb.channel.send(res.get("messages.unknown_channel"))
            return None
        return channel

    @staticmethod
    @_for_type(DIS.Role)
    async def _resolve_role_w_fb(fb: DIS.Message, ext: Any, role_name: str) -> Optional[DIS.Role]:
        role = ext.bot.get_role(role_name)
        if role is None:
            await fb.channel.send(res.get("messages.unknown_role"))
            return None
        return role

    @staticmethod
    @_for_type(OverlordMember)
    async def _resolve_ov_member_w_fb(fb: DIS.Message, ext: Any, user_mention: str) -> Optional[OverlordMember]:
        user = await ext.bot.resolve_user(user_mention)
        if user is None:
            await fb.channel.send(res.get("messages.unknown_user"))
            return None
        try:
            member = await ext.bot.guild.fetch_member(user.id)
        except DIS.NotFound:
            await fb.channel.send(res.get("messages.not_member_user"))
            return None
        return OverlordMember(member, user)