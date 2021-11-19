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
        self.client = ws_client
        self.supported_modules = []

    async def process_data_message(self, message: Any) -> bool:
        """Process incoming data messages for messages of interest"""
        if message.get("result"):
            supported_modules = message["result"].get("objects")
            if supported_modules:
                self.supported_modules = supported_modules
                return True
        return False

    async def _request_api(self, method) -> Any:
        """Request and wait for the response"""
        async with self.client.request(method) as req:
            return await req.get_result()

    async def host_restart(self) -> Any:
        """Send command to restart"""
        return await self._request_api("printer.restart")

    async def info(self) -> Any:
        """Request printer information"""
        return await self._request_api("printer.info")

    async def emergency_stop(self) -> Any:
        """Send emergency stop command."""
        return await self._request_api("printer.emergency_stop")

    async def firmware_restart(self) -> Any:
        """Send firmware restart command."""
        return await self._request_api("printer.firmware_restart")
