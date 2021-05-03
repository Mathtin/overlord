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

import logging
from typing import Dict, Tuple, Optional

import discord

import db as DB
import db.converters as conv
import db.queries as q
from db.predefined import EVENT_TYPES
from .service import DBService

log = logging.getLogger('event-service')


##########################
# Service implementation #
##########################

class EventService(DBService):
    # State
    event_type_map: Dict[str, int]

    def __init__(self, db: DB.DBConnection) -> None:
        super().__init__(db)
        with self.sync_session() as session:
            session.sync_table(model_type=DB.EventType, values=EVENT_TYPES, pk_col='name')
            session.commit()
            self.event_type_map = {row.name: row.id for row in
                                   session.execute(q.select_event_types()).scalars().all()}

    def check_event_name(self, name: str) -> None:
        if name not in self.event_type_map:
            raise NameError(f"No such event name: {name}")

    def type_id(self, event_name: str) -> int:
        return self.event_type_map[event_name]

    ###########
    # GETTERS #
    ###########

    def get_last_vc_event_sync(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[DB.VoiceChatEvent]:
        return self.get_optional_sync(q.select_any_last_vc_event_by_user_id(user.id, channel.id))

    async def get_last_vc_event(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[DB.VoiceChatEvent]:
        return await self.get_optional(q.select_any_last_vc_event_by_user_id(user.id, channel.id))

    def get_last_vc_join_event_sync(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[DB.VoiceChatEvent]:
        return self.get_optional_sync(q.select_last_vc_event_by_user_id(channel.id, 'vc_join', user.id))

    async def get_last_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[DB.VoiceChatEvent]:
        return await self.get_optional(q.select_last_vc_event_by_user_id(channel.id, 'vc_join', user.id))

    def get_last_member_event_sync(self, member: discord.Member) -> Optional[DB.MemberEvent]:
        return self.get_optional_sync(q.select_last_member_event_by_user_did(member.id))

    async def get_last_member_event(self, member: discord.Member) -> Optional[DB.MemberEvent]:
        return await self.get_optional(q.select_last_member_event_by_user_did(member.id))

    def get_last_member_event_for_db_user_sync(self, user: DB.User) -> Optional[DB.MemberEvent]:
        return self.get_optional_sync(q.select_last_member_event_by_user_id(user.id))

    async def get_last_member_event_for_db_user(self, user: DB.User) -> Optional[DB.MemberEvent]:
        return await self.get_optional(q.select_last_member_event_by_user_id(user.id))

    def get_new_message_event_by_did_sync(self, did: int) -> Optional[DB.MessageEvent]:
        return self.get_optional_sync(q.select_message_event_by_did(self.type_id('new_message'), did))

    async def get_new_message_event_by_did(self, did: int) -> Optional[DB.MessageEvent]:
        return await self.get_optional(q.select_message_event_by_did(self.type_id('new_message'), did))

    def get_message_delete_event_by_did_sync(self, did: int) -> Optional[DB.MessageEvent]:
        return self.get_optional_sync(q.select_message_event_by_did(self.type_id('message_delete'), did))

    async def get_message_delete_event_by_did(self, did: int) -> Optional[DB.MessageEvent]:
        return await self.get_optional(q.select_message_event_by_did(self.type_id('message_delete'), did))

    ################
    # CONSTRUCTORS #
    ################

    def create_member_join_event_sync(self, user: DB.User, member: discord.Member) -> DB.MemberEvent:
        return self.create_sync(DB.MemberEvent, conv.member_join_row(user, member.joined_at, self.event_type_map))

    async def create_member_join_event(self, user: DB.User, member: discord.Member) -> DB.MemberEvent:
        return await self.create(DB.MemberEvent, conv.member_join_row(user, member.joined_at, self.event_type_map))

    def create_user_leave_event_sync(self, user: DB.User) -> DB.MemberEvent:
        return self.create_sync(DB.MemberEvent, conv.user_leave_row(user, self.event_type_map))

    async def create_user_leave_event(self, user: DB.User) -> DB.MemberEvent:
        return await self.create(DB.MemberEvent, conv.user_leave_row(user, self.event_type_map))

    def create_new_message_event_sync(self, user: DB.User, message: discord.Message) -> DB.MessageEvent:
        return self.merge_sync(DB.MessageEvent, conv.new_message_to_row(user.id, message, self.event_type_map))

    async def create_new_message_event(self, user: DB.User, message: discord.Message) -> DB.MessageEvent:
        return await self.create(DB.MessageEvent, conv.new_message_to_row(user.id, message, self.event_type_map))

    def create_message_edit_event_sync(self, msg: DB.MessageEvent) -> DB.MessageEvent:
        return self.create_sync(DB.MessageEvent, conv.message_edit_row(msg, self.event_type_map))

    async def create_message_edit_event(self, msg: DB.MessageEvent) -> DB.MessageEvent:
        return await self.create(DB.MessageEvent, conv.message_edit_row(msg, self.event_type_map))

    def create_message_delete_event_sync(self, msg: DB.MessageEvent) -> DB.MessageEvent:
        return self.create_sync(DB.MessageEvent, conv.message_delete_row(msg, self.event_type_map))

    async def create_message_delete_event(self, msg: DB.MessageEvent) -> DB.MessageEvent:
        return await self.create(DB.MessageEvent, conv.message_delete_row(msg, self.event_type_map))

    def create_new_reaction_event_sync(self, user: DB.User, msg: DB.MessageEvent) -> DB.ReactionEvent:
        return self.create_sync(DB.ReactionEvent, conv.new_reaction_to_row(user, msg, self.event_type_map))

    async def create_new_reaction_event(self, user: DB.User, msg: DB.MessageEvent) -> DB.ReactionEvent:
        return await self.create(DB.ReactionEvent, conv.new_reaction_to_row(user, msg, self.event_type_map))

    def create_reaction_delete_event_sync(self, user: DB.User, msg: DB.MessageEvent) -> DB.ReactionEvent:
        return self.create_sync(DB.ReactionEvent, conv.reaction_delete_row(user, msg, self.event_type_map))

    async def create_reaction_delete_event(self, user: DB.User, msg: DB.MessageEvent) -> DB.ReactionEvent:
        return await self.create(DB.ReactionEvent, conv.reaction_delete_row(user, msg, self.event_type_map))

    def create_vc_join_event_sync(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        return self.create_sync(DB.VoiceChatEvent, conv.vc_join_row(user, channel, self.event_type_map))

    async def create_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        return await self.create(DB.VoiceChatEvent, conv.vc_join_row(user, channel, self.event_type_map))

    def create_vc_leave_event_sync(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        return self.create_sync(DB.VoiceChatEvent, conv.vc_leave_row(user, channel, self.event_type_map))

    async def create_vc_leave_event(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        return await self.create(DB.VoiceChatEvent, conv.vc_leave_row(user, channel, self.event_type_map))

    #########
    # OTHER #
    #########

    def clear_text_channel_history_sync(self, channel: discord.TextChannel) -> None:
        self.execute_sync(q.delete_message_events_by_channel_id(channel.id))

    async def clear_text_channel_history(self, channel: discord.TextChannel) -> None:
        await self.execute(q.delete_message_events_by_channel_id(channel.id))

    def repair_member_joined_event_sync(self, member: discord.Member, user: DB.User) -> None:
        with self.sync_session() as session:
            with session.begin():
                last_event_stmt = q.select_last_member_event_by_user_id(user.id)
                last_event = session.execute(last_event_stmt).scalar_one_or_none()
                if last_event is None or last_event.type_id != self.type_id("member_join"):
                    member_join_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
                    last_event = session.add(model_type=DB.MemberEvent, value=member_join_row)
                last_event.created_at = member.joined_at

    async def repair_member_joined_event(self, member: discord.Member, user: DB.User) -> None:
        async with self.session() as session:
            async with session.begin():
                last_event_stmt = q.select_last_member_event_by_user_id(user.id)
                last_event = (await session.execute(last_event_stmt)).scalar_one_or_none()
                if last_event is None or last_event.type_id != self.type_id("member_join"):
                    member_join_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
                    last_event = session.add(model_type=DB.MemberEvent, value=member_join_row)
                last_event.created_at = member.joined_at

    def close_vc_join_event_sync(self,
                                 user: DB.User,
                                 channel: discord.VoiceChannel) -> \
            Optional[Tuple[DB.VoiceChatEvent, DB.VoiceChatEvent]]:
        with self.sync_session() as session:
            with session.begin():
                join_event_stmt = q.select_any_last_vc_event_by_user_id(user.id, channel.id)
                join_event = session.execute_sync(join_event_stmt).scalar_one_or_none()
                if join_event is None or join_event.type_id != self.type_id("vc_join"):
                    log.warning(f'VC join event is absent for {user} in <{channel.name}! Skipping vc leave event!')
                    return None
                # Save event + update previous
                leave_event_row = conv.vc_leave_row(user, channel, self.event_type_map)
                leave_event = session.add(model_type=DB.VoiceChatEvent, value=leave_event_row)
            session.detach(join_event)
            session.detach(leave_event)
            return join_event, leave_event

    async def close_vc_join_event(self,
                                  user: DB.User,
                                  channel: discord.VoiceChannel) -> \
            Optional[Tuple[DB.VoiceChatEvent, DB.VoiceChatEvent]]:
        async with self.session() as session:
            async with session.begin():
                join_event_stmt = q.select_any_last_vc_event_by_user_id(user.id, channel.id)
                join_event = (await session.execute(join_event_stmt)).scalar_one_or_none()
                if join_event is None or join_event.type_id != self.type_id("vc_join"):
                    log.warning(f'VC join event is absent for {user} in <{channel.name}! Skipping vc leave event!')
                    return None
                # Save event + update previous
                leave_event_row = conv.vc_leave_row(user, channel, self.event_type_map)
                leave_event = session.add(model_type=DB.VoiceChatEvent, value=leave_event_row)
                await session.flush([leave_event])
                await session.refresh(leave_event)
                join_event.updated_at = leave_event.created_at
            await session.detach(join_event)
            await session.detach(leave_event)
            return join_event, leave_event

    def repair_vc_leave_event_sync(self, user: DB.User, channel: discord.VoiceChannel) -> None:
        with self.sync_session() as session:
            with session.begin():
                last_event_stmt = q.select_any_last_vc_event_by_user_id(user.id, channel.id)
                last_event = session.execute(last_event_stmt).scalar_one_or_none()
                if last_event is not None and last_event.type_id == self.type_id("vc_join"):
                    log.warning(f'Closing VC leave event not found for {user} in <{channel.name} (removing vc_join '
                                f'event)')
                    session.delete(model=last_event)

    async def repair_vc_leave_event(self, user: DB.User, channel: discord.VoiceChannel) -> None:
        async with self.session() as session:
            async with session.begin():
                last_event_stmt = q.select_any_last_vc_event_by_user_id(user.id, channel.id)
                last_event = (await session.execute(last_event_stmt)).scalar_one_or_none()
                if last_event is not None and last_event.type_id == self.type_id("vc_join"):
                    log.warning(f'Closing VC leave event not found for {user} in <{channel.name} (removing vc_join '
                                f'event)')
                    await session.delete(model=last_event)

    def clear_all_sync(self):
        with self.sync_session() as session:
            with session.begin():
                session.execute(q.delete_all(DB.VoiceChatEvent))
                session.execute(q.delete_all(DB.ReactionEvent))
                session.execute(q.delete_all(DB.MessageEvent))
                session.execute(q.delete_all(DB.MemberEvent))

    async def clear_all(self):
        async with self.session() as session:
            async with session.begin():
                await session.execute(q.delete_all(DB.VoiceChatEvent))
                await session.execute(q.delete_all(DB.ReactionEvent))
                await session.execute(q.delete_all(DB.MessageEvent))
                await session.execute(q.delete_all(DB.MemberEvent))
