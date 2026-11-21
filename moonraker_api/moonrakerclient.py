# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

"""Moonraker client API."""

from __future__ import annotations

from typing import Any, Literal

from moonraker_api.websockets.websocketclient import (
    WebsocketClient,
    WebsocketStatusListener,
)


class MoonrakerListener(WebsocketStatusListener):
    """Base lass providing functions to receive events from the
    moonraker API"""


class MoonrakerClient(WebsocketClient):
    """Moonraker API client class, repesents an API instance

    Attributes:
      host: hostname or IP address of the printer
      port: Defaults to 7125
    """

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

    async def get_temperature_sensors(self) -> list[str] | None:
        """Get registered thermal object names after Klipper is ready.

        Return [] when no sources are registered, or None when the RPC reply
        has no status result.
        """
        response = await self.call_method(
            "printer.objects.query",
            objects={"heaters": ["available_sensors", "available_monitors"]},
        )
        if "status" not in response:
            return None

        heaters = response["status"].get("heaters", {})
        sensors = heaters.get("available_sensors", [])
        monitors = heaters.get("available_monitors") or []
        return list(dict.fromkeys([*sensors, *monitors]))

    async def get_klipper_status(self) -> Literal["ready", "shutdown", "disconnected"]:
        """Returns the current status of klipper."""
        info = await self.call_method("server.info")
        return info["klippy_state"]

    async def get_websocket_id(self) -> Any:
        """Get the connected websocket id."""
        return await self.call_method("server.websocket.id")
