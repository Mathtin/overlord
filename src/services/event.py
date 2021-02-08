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

import logging

import discord
import db as DB
import db.converters as conv
import db.queries as q

from typing import Dict, Tuple, Optional

log = logging.getLogger('event-service')

##########################
# Service implementation #
##########################

class EventService(object):

    # State
    event_type_map: Dict[str, int]

    # Members passed via constructor
    db: DB.DBSession

    def __init__(self, db: DB.DBSession) -> None:
        self.db = db
        self.event_type_map = {row.name:row.id for row in self.db.query(DB.EventType)}

    def check_event_name(self, name: str) -> None:
        if name not in self.event_type_map:
            raise NameError(f"No such event name: {name}")

    def get_last_vc_event(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[DB.VoiceChatEvent]:
        return q.get_last_vc_event_by_id(self.db, user.id, channel.id)

    def get_last_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[DB.VoiceChatEvent]:
        return q.get_last_vc_event_by_id_and_type_id(self.db, user.id, channel.id, self.type_id("vc_join"))

    def get_last_member_event(self, member: discord.Member) -> Optional[DB.MemberEvent]:
        return q.get_last_member_event_by_did(self.db, member.id)

    def get_last_user_member_event(self, user: DB.User) -> Optional[DB.MemberEvent]:
        return q.get_last_member_event_by_id(self.db, user.id)

    def get_message(self, did: int) -> Optional[DB.MessageEvent]:
        return q.get_msg_by_did(self.db, did)

    def type_id(self, event_name: str) -> int:
        return self.event_type_map[event_name]

    def repair_member_joined_event(self, member: discord.Member, user: DB.User) -> None:
        last_event = self.get_last_user_member_event(user)
        if last_event is None or last_event.type_id != self.type_id("member_join"):
            e_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
            last_event = self.db.add(DB.MemberEvent, e_row)
        last_event.created_at = member.joined_at
        self.db.commit()

    def repair_vc_leave_event(self, user: DB.User, channel: discord.VoiceChannel) -> None:
        last_event = self.get_last_vc_event(user, channel)
        if last_event is not None and last_event.type_id == self.type_id("vc_join"):
            log.warn(f'VC leave event is absent for last vc_join event for {user} in <{channel.name}! Removing last vc_join event!')
            self.db.delete_model(last_event)
            self.db.commit()

    def create_member_join_event(self, user: DB.User, member: discord.Member) -> DB.MemberEvent:
        e_row = conv.member_join_row(user, member.joined_at, self.event_type_map)
        res = self.db.add(DB.MemberEvent, e_row)
        self.db.commit()
        return res

    def create_user_leave_event(self, user: DB.User) -> DB.MemberEvent:
        e_row = conv.user_leave_row(user, self.event_type_map)
        res = self.db.add(DB.MemberEvent, e_row)
        self.db.commit()
        return res

    def create_new_message_event(self, user: DB.User, message: discord.Message) -> DB.MessageEvent:
        row = conv.new_message_to_row(user.id, message, self.event_type_map)
        res = self.db.add(DB.MessageEvent, row)
        self.db.commit()
        return res

    def create_message_edit_event(self, msg: DB.MessageEvent) -> DB.MessageEvent:
        row = conv.message_edit_row(msg, self.event_type_map)
        res = self.db.add(DB.MessageEvent, row)
        self.db.commit()
        return res

    def create_message_delete_event(self, msg: DB.MessageEvent) -> DB.MessageEvent:
        row = conv.message_delete_row(msg, self.event_type_map)
        res = self.db.add(DB.MessageEvent, row)
        self.db.commit()
        return res

    def create_new_reaction_event(self, user: DB.User, msg: DB.MessageEvent) -> DB.ReactionEvent:
        row = conv.new_reaction_to_row(user, msg, self.event_type_map)
        res = self.db.add(DB.ReactionEvent, row)
        self.db.commit()
        return res

    def create_reaction_delete_event(self, user: DB.User, msg: DB.MessageEvent) -> DB.ReactionEvent:
        row = conv.reaction_delete_row(user, msg, self.event_type_map)
        res = self.db.add(DB.ReactionEvent, row)
        self.db.commit()
        return res

    def create_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        e_row = conv.vc_join_row(user, channel, self.event_type_map)
        res = self.db.add(DB.VoiceChatEvent, e_row)
        self.db.commit()
        return res

    def create_vc_leave_event(self, user: DB.User, channel: discord.VoiceChannel) -> DB.VoiceChatEvent:
        e_row = conv.vc_leave_row(user, channel, self.event_type_map)
        res = self.db.add(DB.VoiceChatEvent, e_row)
        self.db.commit()
        return res

    def close_vc_join_event(self, user: DB.User, channel: discord.VoiceChannel) -> Optional[Tuple[DB.VoiceChatEvent, DB.VoiceChatEvent]]:
        join_event = self.get_last_vc_event(user, channel)
        if join_event is None or join_event.type_id != self.type_id("vc_join"):
            # Skip absent vc join
            log.warn(f'VC join event is absent for {user} in <{channel.name}! Skipping vc leave event!')
            return None
        # Save event + update previous
        e_row = conv.vc_leave_row(user, channel, self.event_type_map)
        leave_event = self.db.add(DB.VoiceChatEvent, e_row)
        self.db.commit()
        return join_event, leave_event

    def clear_text_channel_history(self, channel: discord.TextChannel) -> None:
        self.db.query(DB.MessageEvent).filter_by(channel_id=channel.id).delete()
        self.db.commit()

