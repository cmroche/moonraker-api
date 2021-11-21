# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

"""Moonraker client API."""

from __future__ import annotations

import logging
from asyncio.events import AbstractEventLoop
from typing import Any, Literal

import aiohttp
from aiohttp.web_response import Response

from moonraker_api.const import WEBSOCKET_CONNECTION_TIMEOUT
from moonraker_api.websockets.websocketclient import (
    WebsocketClient,
    WebsocketStatusListener,
)

_LOGGER = logging.getLogger(__name__)


class MoonrakerListener(WebsocketStatusListener):
    """Base lass providing functions to receive events from the
    moonraker API"""


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
        api_key: str | None = None,
        ssl: bool = False,
        loop: AbstractEventLoop = None,
        timeout: int = WEBSOCKET_CONNECTION_TIMEOUT,
        session: aiohttp.ClientSession = None,
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
            self, listener, host, port, api_key, ssl, loop, timeout, session
        )

    async def _loop_recv_internal(self, message: Any) -> None:
        """Private method to allow processing if incoming messages"""
        # Empty for the moment

    async def call_method(self, method: str, **kwargs: Any) -> Any:
        """Call a json-rpc method and wait for the response.

        Args:
            **kwargs (optional): Used to pass RPC ``params`` to the call.

        Returns:
            A ``json`` object containing the ``response`` of the RPC method.
        """
        async with self.request(method, **kwargs) as req:
            return await req.get_result()

    async def get_host_info(self) -> Any:
        """Get the connected websocket id."""
        return await self.call_method("printer.info")

    async def get_server_info(self) -> Any:
        """Get the connected websocket id."""
        return await self.call_method("server.info")

    async def get_supported_modules(self) -> list[str] | None:
        """Get supported modules from Klipper."""
        response = await self.call_method("printer.objects.list")
        if "objects" in response:
            return response["objects"]
        return None

    async def get_klipper_status(self) -> Literal["ready", "shutdown", "disconnected"]:
        """Returns the current status of klipper."""
        info = await self.call_method("server.info")
        return info["klippy_state"]

    async def get_websocket_id(self) -> Any:
        """Get the connected websocket id."""
        return await self.call_method("server.websocket.id")
