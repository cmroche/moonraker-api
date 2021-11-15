# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
from asyncio.events import AbstractEventLoop
import logging

from typing import Any

_LOGGER = logging.getLogger(__name__)


class WebsocketWaitableTask:
    """Class representing a waitable request.

    The intended use is to create potentially long running
    tasks, such as requests for data from an API endpoint
    and provide a signal for completion of the task.
    """

    def __init__(self, timeout: int = 120, loop: AbstractEventLoop = None):
        """Initialize the class, and wait event"""
        self._event = asyncio.Event()
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop_policy().get_event_loop()
        self._task = asyncio.create_task(
            asyncio.wait_for(self._event.wait(), timeout=self._timeout)
        )

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

    async def wait(self):
        """Wait for the task to be completed, up to the timeout"""
        return await self._task
