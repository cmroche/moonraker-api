# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import logging

from typing import Any, Coroutine
from moonraker_api.websockets.websocketclient import WebsocketClient
from moonraker_api.websockets.websocketdatahandler import WebsocketDataHandler

_LOGGER = logging.getLogger(__name__)


class PrinterAdminstration(WebsocketDataHandler):
    """Class holding printer administration data.

    Attributes:
        objects (List[str]): List of supported modules by the API
    """

    def __init__(self, ws_client: WebsocketClient):
        """Class initializer

        Args:
            ws_client (WebsocketClient): Websocket session client
        """
        self._ws_client = ws_client
        self.supported_modules = []

    async def process_data_message(self, message: Any) -> bool:
        """Process incoming data messages for messages of interest"""
        supported_modules = message.get("objects")
        if supported_modules:
            self.supported_modules = supported_modules
            return True
        return False

    async def restart(self) -> Coroutine:
        """Send command to restart"""
        async with self._ws_client.request("printer.restart") as req:
            return await req.result()

    async def info(self) -> Coroutine:
        """Request printer information"""
        async with self._ws_client.request("printer.info") as req:
            return await req.result()
