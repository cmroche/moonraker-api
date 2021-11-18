# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import logging

from asyncio.events import AbstractEventLoop
from typing import Any

from moonraker_api.const import WEBSOCKET_CONNECTION_TIMEOUT
from moonraker_api.data_types.printeradministration import PrinterAdminstration

from moonraker_api.websockets.websocketclient import (
    WebsocketClient,
    WebsocketStatusListener,
)

_LOGGER = logging.getLogger(__name__)


class MoonrakerListener(WebsocketStatusListener):
    """Base lass providing functions to receive events from the
    moonraker API"""

    async def state_changed(self, state: str) -> None:
        """Called when the websocket state changes"""


class MoonrakerClient(WebsocketClient):
    """Moonraker API client class, repesents an API instance

    Attributes:
      host: hostname or IP address of the printer
      port: Defaults to 7125
    """

    def __init__(
        self,
        listener: MoonrakerListener,
        host: str,
        port: int = 7125,
        retry: bool = True,
        api_key: str = None,
        loop: AbstractEventLoop = None,
        timeout: int = WEBSOCKET_CONNECTION_TIMEOUT,
    ) -> None:
        """Initialize the moonraker client object

        Args:
            listener (MoonrakerListen): Event listener
            host (str): hostname or IP address of the printer
            port (int, optional): Defaults to 7125
            api_key (str, optional): API key
            loop (AbstractEventLoop, option):
                Provide an optional asyncio loop for tasks
            timeout (int, option): Timeout in seconds for websockets
        """
        WebsocketClient.__init__(
            self, listener, host, port, api_key, retry, loop, timeout
        )

        self.modules = {
            "printer_administration": PrinterAdminstration(self),
        }

    @property
    def authorization(self):
        """Return ``Authorization`` object"""
        return self.modules["authorization"]

    @property
    def printer_administration(self):
        """Returns ``PrinterAdministation`` object"""
        return self.modules["printer_administration"]

    async def _loop_recv_internal(self, message: Any) -> None:
        """Private method to allow processing if incoming messages"""
        for module in self.modules.values():
            if await module.process_data_message(message):
                break
