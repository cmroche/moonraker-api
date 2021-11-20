# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license
"""Awaitable tasks."""
from __future__ import annotations

import asyncio
import logging
from asyncio.events import AbstractEventLoop
from typing import Any, Coroutine, Generic, TypeVar

_LOGGER = logging.getLogger(__name__)

_RetType = TypeVar("_RetType")


class AwaitableTask:
    """Class representing a waitable request.

    The intended use is to create potentially long running
    tasks, such as requests for data from an API endpoint
    and provide a signal for completion of the task.
    """

    def __init__(
        self, req_id: int, timeout: int = 120, loop: AbstractEventLoop = None
    ) -> None:
        """Initialize the class, and wait event"""
        self._req_id = req_id
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop_policy().get_event_loop()
        self._result = self._loop.create_future()
        self._task = asyncio.create_task(
            asyncio.wait_for(self._result, timeout=self._timeout)
        )

    @property
    def req_id(self) -> int:
        """ID of the AwaitableTask"""
        return self._req_id

    @property
    def timeout(self) -> int:
        """Return the timeout time in seconds"""
        return self._timeout

    @property
    def done(self) -> bool:
        """Return the current status of our waiting task"""
        return self._result.done()

    async def get_result(self) -> Any:
        """Return result or request"""
        await self._task
        return self._result.result()

    def set_result(self, result: Any) -> None:
        """Sets the task as complete"""
        self._result.set_result(result)

    @property
    def exception(self) -> BaseException:
        """Return exception of request"""
        return self._result.exception()

    def set_exception(self, exception: type | BaseException) -> None:
        """Set the exception for the request"""
        self._result.set_exception(exception)

    async def wait(self):
        """Wait for the task to be completed, up to the timeout"""
        return await self._task

    def cancel(self):
        """Cancel any requests still waiting for a response"""
        self._result.cancel()


class AwaitableTaskContext(Generic[_RetType]):
    """Async context manager for awaitable tasks"""

    def __init__(
        self,
        coro: Coroutine["asyncio.Future[Any]", None, _RetType],
        tasks: dict[int, _RetType],
    ) -> None:
        self._coro = coro
        self._tasks = tasks
        self._task = None

    @property
    def tasks(self) -> dict[int, _RetType]:
        """Return the current dictionary of ids and tasks"""
        return self._tasks

    async def __aenter__(self) -> _RetType:
        """Add the current task to the task list"""
        task = await self._coro
        self._task = task
        self._tasks[task.req_id] = task
        return task

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        """Remove the current task from the task list"""
        self._tasks.pop(self._task.req_id)
