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

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session, sessionmaker

from db.models.base import Base, BaseModel
from db.models import *

log = getLogger()

class DBSession(object):

    _session: Session

    # Main DB Connection Ref Obj
    db_engine = None

    def __init__(self, autocommit=True, autoflush=True):
        engine_url = os.getenv('DATABASE_ACCESS_URL')
        log.info(f'Connecting to {engine_url}')
        self.db_engine = create_engine(engine_url)
        Base.metadata.create_all(self.db_engine)
        session_factory = sessionmaker(bind=self.db_engine, autocommit=autocommit, autoflush=autoflush)
        self._session = session_factory()

    def query(self, *entities, **kwargs):
        return self._session.query(*entities, **kwargs)

    def add(self, model: BaseModel, need_flush: bool = False):
        self._session.add(model)

        if need_flush:
            self._session.flush([model])

    def add_all(self, models: list):
        self._session.add_all(models)

    def delete(self, model: BaseModel):
        if model is None:
            log.warning(f'{__name__}: model is None')

        try:
            self._session.delete(model)
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
        except DataError as e:
            log.error(f'`{__name__}` {e}')

    def commit(self, need_close: bool = False):
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
        index = {}
        for v in values:
            index[v[pk]] = v

        for row in self.query(model):
            p = getattr(row, pk)
            if p not in index:
                self.delete(row)
                continue
            new_values = index[p]
            for col in new_values:
                if getattr(row, col) != new_values[col]:
                    setattr(row, col, new_values[col])
            del index[p]

        for id in index:
            new_values = index[id]
            row = model(**new_values)
            self.add(row)

    def update_or_add(self, model: BaseModel, pk: str, value: dict):
        if not self.update(model, pk, value):
            self.add(model(**value))

    def update(self, model: BaseModel, pk: str, value: dict):
        row = self.query(model).filter_by(**{pk:value[pk]}).first()
        if row is None:
            return False
        for col in value:
            if getattr(row, col) != value[col]:
                setattr(row, col, value[col])
        return True

    def close(self):
        try:
            self._session.close()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise
