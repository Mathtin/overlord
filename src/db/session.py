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

    _session: Session
    _last_connection: datetime

    # Main DB Connection Ref Obj
    db_engine = None
    session_factory = None

    def __init__(self, engine_url, autocommit=True, autoflush=True):
        self.engine_url = engine_url
        log.info(f'Connecting to database')
        self.db_engine = create_engine(self.engine_url, pool_recycle=60)
        Base.metadata.create_all(self.db_engine)
        self.session_factory = sessionmaker(bind=self.db_engine, autocommit=autocommit, autoflush=autoflush)
        self._last_connection = None
        self._session = None
        self._check_connection()

    def _check_connection(self):
        now = datetime.now()
        if self._last_connection is None or (now - self._last_connection).total_seconds() > 10:
            if self._session is not None:
                self._session.close()
            self._session = self.session_factory()
            self._last_connection = now

    def query(self, *entities, **kwargs):
        self._check_connection()
        return self._session.query(*entities, **kwargs)

    def execute(self, *entities, **kwargs):
        self._check_connection()
        return self._session.execute(*entities, **kwargs)

    def add(self, model: BaseModel, value: dict, need_flush: bool = False):
        row = model(**value)
        self.add_model(row, need_flush=need_flush)
        return row

    def add_model(self, model: BaseModel, need_flush: bool = False):
        self._check_connection()
        self._session.add(model)
        if need_flush:
            self._session.flush([model])

    def add_all(self, models: list):
        self._check_connection()
        self._session.add_all(models)

    def delete(self, model: BaseModel, pk: str, value: dict):
        row = self.query(model).filter_by(**{pk:value[pk]}).first()
        if row is None:
            return None
        self.delete_model(row)
        return row

    def delete_model(self, model: BaseModel):
        self._check_connection()
        try:
            self._session.delete(model)
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
        except DataError as e:
            log.error(f'`{__name__}` {e}')

    def commit(self, need_close: bool = False):
        self._check_connection()
        try:
            self._session.commit()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise

        if need_close:
            self.close_session()

    def sync_table(self, model: BaseModel, pk: str, values: list):
        self._check_connection()
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
        self._check_connection()
        row = self.query(model).filter_by(**{pk:value[pk]}).first()
        if row is None:
            return None
        for col in value:
            if getattr(row, col) != value[col]:
                setattr(row, col, value[col])
        return row

    def touch(self, model: BaseModel, id: int):
        self._check_connection()
        stmt = update(model).where(model.id == id)
        self.execute(stmt)

    def close(self):
        try:
            self._session.close()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise
