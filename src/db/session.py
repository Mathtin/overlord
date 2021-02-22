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

from sqlalchemy import engine as SyncEngine, create_engine, select, update
from sqlalchemy.engine import Result
from sqlalchemy.exc import IntegrityError, DataError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, AsyncResult, AsyncSessionTransaction
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker, Session, SessionTransaction
from aiosqlite3.sa import create_engine as create_aiosqlite_engine

from .models.base import Base, BaseModel

log = getLogger('db')


class DBSyncSession(object):
    _session: Session

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._session.__exit__(exc_type, exc_val, exc_tb)

    ########################
    # Base session methods #
    ########################

    def execute(self, statement: Any) -> Result:
        return self._session.execute(statement)

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise

    def rollback(self) -> None:
        self._session.rollback()

    def begin(self) -> SessionTransaction:
        return self._session.begin()

    def refresh(self, instance, attribute_names=None, with_for_update=None) -> None:
        self._session.refresh(instance, attribute_names, with_for_update)

    def expunge(self, model: BaseModel) -> None:
        self._session.expunge(model)

    def detach(self, model: BaseModel) -> None:
        try:
            self.refresh(model)
            self.expunge(model)
        except InvalidRequestError:
            pass

    ##############################
    # Dict based session methods #
    ##############################

    def get(self, model_type: Type[BaseModel], pk: int) -> BaseModel:
        return self._session.get(model_type, pk)

    def add(self, *, model: BaseModel = None, model_type: Type[BaseModel] = None, value: Dict[str, Any] = None) -> \
            BaseModel:
        if model is None:
            model = model_type(**value)
        self._session.add(model)
        return model

    def merge(self, *, model: BaseModel = None, model_type: Type[BaseModel] = None, value: Dict[str, Any] = None) -> \
            BaseModel:
        if model is None:
            model = model_type(**value)
        self._session.merge(model)
        return model

    def delete(self, *, model: BaseModel = None, model_type: Type[BaseModel] = None, pk: int = None) -> \
            Optional[BaseModel]:
        if model is None:
            model = self.get(model_type, pk)
            if model is None:
                return None
        self.detach(model)
        model_copy = self.get(model_type, pk)
        if model is None:
            return None
        self._session.delete(model_copy)
        return model

    def touch(self, *, model: BaseModel = None, model_type: Type[BaseModel] = None, pk: int = None) -> None:
        if model is None:
            self.execute(update(model_type).where(model_type.id == pk))
        else:
            self.execute(update(model_type).where(model_type.id == model.id))

    def update(self, model_type: Type[BaseModel], value: Dict[str, Any]) -> Optional[BaseModel]:
        row = self.get(model_type, value['id'])
        if row is None:
            return None
        for col in value:
            if getattr(row, col) != value[col]:
                setattr(row, col, value[col])
        return row

    ###################
    # Special methods #
    ###################

    def sync_table(self, model_type: Type[BaseModel], values: List[Dict[str, Any]]):
        # In-memory table index
        index = {}
        for v in values:
            index[v['id']] = v
        # Sync existing rows
        for row in self.execute(select(model_type)).scalars().all():
            # Remove not in values
            if row.id not in index:
                row.delete()
                continue
            # Update those are in values
            new_values = index[row.id]
            for col in new_values:
                if getattr(row, col) != new_values[col]:
                    setattr(row, col, new_values[col])
            del index[row.id]
        # Add absent
        for id_ in index:
            new_value = index[id_]
            self.add(model_type=model_type, value=new_value)


class DBAsyncSession(object):
    _session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.__aexit__(exc_type, exc_val, exc_tb)

    ########################
    # Base session methods #
    ########################

    async def execute(self, statement: Any) -> Result:
        return await self._session.execute(statement)

    async def stream(self, statement: Any) -> AsyncResult:
        return await self._session.stream(statement)

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as e:
            log.error(f'`{__name__}` {e}')
            raise
        except DataError as e:
            log.error(f'`{__name__}` {e}')
            raise

    async def rollback(self) -> None:
        await self._session.rollback()

    async def begin(self) -> AsyncSessionTransaction:
        return await self._session.begin()

    async def refresh(self, instance, attribute_names=None, with_for_update=None):
        await self._session.refresh(instance, attribute_names, with_for_update)

    async def expunge(self, model: BaseModel) -> None:
        await self._session.expunge(model)

    async def detach(self, model: BaseModel) -> None:
        try:
            await self.refresh(model)
            await self.expunge(model)
        except InvalidRequestError:
            pass

    ##############################
    # Dict based session methods #
    ##############################

    async def get(self, model_type: Type[BaseModel], pk: int) -> BaseModel:
        return await self._session.get(model_type, pk)

    async def add(self, *, model: BaseModel = None,
                  model_type: Type[BaseModel] = None,
                  value: Dict[str, Any] = None) -> BaseModel:
        if model is None:
            model = model_type(**value)
        await self._session.add(model)
        return model

    async def merge(self, *, model: BaseModel = None,
                    model_type: Type[BaseModel] = None,
                    value: Dict[str, Any] = None) -> BaseModel:
        if model is None:
            model = model_type(**value)
        await self._session.merge(model)
        return model

    async def delete(self, *, model: BaseModel = None,
                     model_type: Type[BaseModel] = None, pk: int = None) -> Optional[BaseModel]:
        if model is None:
            model = self.get(model_type, pk)
            if model is None:
                return None
        await self.detach(model)
        model_copy = self.get(model_type, pk)
        if model is None:
            return None
        await self._session.delete(model_copy)
        return model

    async def touch(self, *, model: BaseModel = None, model_type: Type[BaseModel] = None, pk: int = None) -> None:
        if model is None:
            await self.execute(update(model_type).where(model_type.id == pk))
        else:
            await self.execute(update(model_type).where(model_type.id == model.id))

    async def update(self, model_type: Type[BaseModel], value: Dict[str, Any]) -> Optional[BaseModel]:
        row = await self.get(model_type, value['id'])
        if row is None:
            return None
        for col in value:
            if getattr(row, col) != value[col]:
                setattr(row, col, value[col])
        return row

    ###################
    # Special methods #
    ###################

    async def sync_table(self, model_type: Type[BaseModel], values: List[Dict[str, Any]]):
        # In-memory table index
        index = {}
        for v in values:
            index[v['id']] = v
        # Sync existing rows
        async for row in await self.stream(select(model_type)):
            # Remove not in values
            if row.id not in index:
                row.delete()
                continue
            # Update those are in values
            new_values = index[row.id]
            for col in new_values:
                if getattr(row, col) != new_values[col]:
                    setattr(row, col, new_values[col])
            del index[row.id]
        # Add absent
        for id_ in index:
            new_value = index[id_]
            await self.add(model_type=model_type, value=new_value)


class DBSessionProvider(object):
    _db_async_engine: AsyncEngine
    _db_sync_engine: SyncEngine
    _session_sync_factory: sessionmaker
    _session_async_factory: sessionmaker

    _sync_session: Optional[DBSyncSession]
    _async_session: Optional[DBAsyncSession]

    def __init__(self, engine_url: str) -> None:
        # Create sync backend
        self._db_sync_engine = create_engine(engine_url)
        Base.metadata.create_all(self._db_sync_engine)
        self._session_sync_factory = sessionmaker(bind=self._db_sync_engine,
                                                  autocommit=False,
                                                  autoflush=True,
                                                  expire_on_commit=False)
        # Create async backend
        if 'sqlite' in engine_url:
            self._db_async_engine = create_aiosqlite_engine(engine_url)
        else:
            self._db_async_engine = create_async_engine(engine_url)
        self._session_async_factory = sessionmaker(bind=self._db_sync_engine,
                                                   autocommit=False,
                                                   autoflush=True,
                                                   class_=AsyncSession,
                                                   expire_on_commit=False)
        self._sync_session = None
        self._async_session = None

    @property
    def sync_session(self):
        return DBSyncSession(self._session_sync_factory())

    @property
    def async_session(self):
        return DBAsyncSession(self._session_async_factory())
