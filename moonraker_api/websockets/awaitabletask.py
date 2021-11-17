# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
from asyncio.events import AbstractEventLoop
import logging

from typing import Any, Coroutine, Dict, Generic, TypeVar

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
        self._event = asyncio.Event()
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop_policy().get_event_loop()
        self._task = asyncio.create_task(
            asyncio.wait_for(self._event.wait(), timeout=self._timeout)
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
    def is_complete(self) -> bool:
        """Return the current status of our waiting task"""
        return self._event.is_set()

    def set_complete(self) -> None:
        """Sets the task as complete"""
        self._event.set()

    async def wait(self):
        """Wait for the task to be completed, up to the timeout"""
        return await self._task

    def cancel(self):
        """Cancel any requests still waiting for a response"""
        self._task.cancel()


class AwaitableTaskContext(Generic[_RetType]):
    """Async context manager for awaitable tasks"""

    def __init__(
        self,
        coro: Coroutine["asyncio.Future[Any]", None, _RetType],
        tasks: Dict[int, _RetType],
    ) -> None:
        self._coro = coro
        self._tasks = tasks
        self._task = None

    @property
    def tasks(self) -> Dict[int, _RetType]:
        """Return the current dictionary of ids and tasks"""
        return self._tasks

    async def __aenter__(self) -> _RetType:
        """Add the current task to the task list"""
        task = await self._coro
        self._task = task
        self._tasks[task.req_id] = task
        return task

    async def __aexit__(self, *args, **kwargs) -> None:
        """Remove the current task from the task list"""
        self._tasks.pop(self._task.req_id)
