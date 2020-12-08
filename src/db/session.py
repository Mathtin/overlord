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

from logging import getLogger
from datetime import datetime

from sqlalchemy import create_engine, update
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.event import listens_for as event_listens_for

from db.models.base import Base, BaseModel
from db.models import *

log = getLogger('db')  


class DBSession(object):

    __session: Session

    # Main DB Connection Ref Obj
    db_engine = None
    session_factory = None

    def __init__(self, engine_url, autocommit=True, autoflush=True):
        self.engine_url = engine_url
        log.info(f'Connecting to database')
        self.db_engine = create_engine(self.engine_url, pool_recycle=60)
        Base.metadata.create_all(self.db_engine)
        self.session_factory = sessionmaker(bind=self.db_engine, autocommit=autocommit, autoflush=autoflush)
        self.__last_connection = None
        self.__check_connection()

    def __check_connection(self):
        now = datetime.now()
        if self.__last_connection is None or (now - self.__last_connection).total_seconds() > 4:
            self.__session = self.session_factory()
            self.__last_connection = now

    def query(self, *entities, **kwargs):
        self.__check_connection()
        return self.__session.query(*entities, **kwargs)

    def execute(self, *entities, **kwargs):
        self.__check_connection()
        return self.__session.execute(*entities, **kwargs)

    def add(self, model: BaseModel, value: dict, need_flush: bool = False):
        row = model(**value)
        self.add_model(row, need_flush=need_flush)
        return row

    def add_model(self, model: BaseModel, need_flush: bool = False):
        self.__check_connection()
        self.__session.add(model)
        if need_flush:
            self.__session.flush([model])

    def add_all(self, models: list):
        self.__check_connection()
        self.__session.add_all(models)

    def delete(self, model: BaseModel, pk: str, value: dict):
        row = self.query(model).filter_by(**{pk:value[pk]}).first()
        if row is None:
            return None
        self.delete_model(row)
        return row

    def delete_model(self, model: BaseModel):
        self.__check_connection()
        try:
            self.__session.delete(model)
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
        except DataError as e:
            log.error(f'`{__name__}` {e}')

    def commit(self, need_close: bool = False):
        self.__check_connection()
        try:
            self.__session.commit()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise

        if need_close:
            self.close_session()

    def sync_table(self, model: BaseModel, pk: str, values: list):
        self.__check_connection()
        index = {}
        for v in values:
            index[v[pk]] = v

        for row in self.query(model):
            p = getattr(row, pk)
            if p not in index:
                self.delete_model(row)
                continue
            new_values = index[p]
            for col in new_values:
                if getattr(row, col) != new_values[col]:
                    setattr(row, col, new_values[col])
            del index[p]
        self.commit()

        for id in index:
            new_values = index[id]
            self.add(model, new_values)
        self.commit()

    def update_or_add(self, model: BaseModel, pk: str, value: dict):
        res = self.update(model, pk, value)
        if res is None:
            return self.add(model, value)
        return res

    def update(self, model: BaseModel, pk: str, value: dict):
        self.__check_connection()
        row = self.query(model).filter_by(**{pk:value[pk]}).first()
        if row is None:
            return None
        for col in value:
            if getattr(row, col) != value[col]:
                setattr(row, col, value[col])
        return row

    def touch(self, model: BaseModel, id: int):
        self.__check_connection()
        stmt = update(model).where(model.id == id)
        self.execute(stmt)

    def close(self):
        try:
            self.__session.close()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise
