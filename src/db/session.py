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

from logging import getLogger
from typing import Type, Optional, Any, Dict, List

from sqlalchemy import create_engine, update, engine as SQLEngine
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import Session, sessionmaker, Query

from .models.base import Base, BaseModel

log = getLogger('db')


class DBPersistSession(object):

    _db_engine: SQLEngine
    _session_factory: sessionmaker = None
    _session: Optional[Session] = None

    def __init__(self, engine_url) -> None:
        self._db_engine = create_engine(engine_url, pool_recycle=60)
        Base.metadata.create_all(self._db_engine)
        self._session_factory = sessionmaker(bind=self._db_engine, autocommit=False, autoflush=True,
                                             expire_on_commit=False)

    def _keep_session(self) -> None:
        if self._session is None:
            self._session = self._session_factory()

    ########################
    # Base session methods #
    ########################

    def query(self, *entities, **kwargs) -> Query:
        self._keep_session()
        return self._session.query(*entities, **kwargs)

    def execute(self, *entities, **kwargs) -> Any:
        self._keep_session()
        return self._session.execute(*entities, **kwargs)

    def commit(self) -> None:
        if self._session is None:
            return
        try:
            self._session.commit()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise
        # self._session.close()
        # self._session = None

    ###############################
    # Model based session methods #
    ###############################

    def add_model(self, model: BaseModel) -> None:
        self._keep_session()
        self._session.add(model)

    def add_all(self, models: List[BaseModel]) -> None:
        self._keep_session()
        self._session.add_all(models)

    def delete_model(self, model: BaseModel) -> None:
        self._keep_session()
        try:
            self._session.delete(model)
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
        except DataError as e:
            log.error(f'`{__name__}` {e}')

    ##############################
    # Dict based session methods #
    ##############################

    def add(self, model: Type[BaseModel], value: Dict[str, Any]) -> BaseModel:
        row = model(**value)
        self.add_model(row)
        return row

    def delete(self, model: Type[BaseModel], pk: str, value: Dict[str, Any]) -> Optional[BaseModel]:
        row = self.query(model).filter_by(**{pk: value[pk]}).first()
        if row is None:
            return None
        self.delete_model(row)
        return row

    def update_or_add(self, model: Type[BaseModel], pk: str, value: dict) -> BaseModel:
        res = self.update(model, pk, value)
        if res is None:
            return self.add(model, value)
        return res

    def update(self, model: Type[BaseModel], pk: str, value: dict) -> Optional[BaseModel]:
        row = self.query(model).filter_by(**{pk: value[pk]}).first()
        if row is None:
            return None
        for col in value:
            if getattr(row, col) != value[col]:
                setattr(row, col, value[col])
        return row

    def touch(self, model: BaseModel, id_: int) -> None:
        stmt = update(model).where(model.id == id_)
        self.execute(stmt)

    ###################
    # Special methods #
    ###################

    def sync_table(self, model: Type[BaseModel], pk: str, values: list):
        # In-memory table index
        index = {}
        for v in values:
            index[v[pk]] = v
        # Sync existing rows
        for row in self.query(model):
            p = getattr(row, pk)
            # Remove not in values
            if p not in index:
                self.delete_model(row)
                continue
            # Update those are in values
            new_values = index[p]
            for col in new_values:
                if getattr(row, col) != new_values[col]:
                    setattr(row, col, new_values[col])
            del index[p]
        self.commit()
        # Add absent
        for id_ in index:
            new_values = index[id_]
            self.add(model, new_values)
        self.commit()
