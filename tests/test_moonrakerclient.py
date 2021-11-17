# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
import pytest

from unittest.mock import patch
from moonraker_api.const import (
    WEBSOCKET_STATE_CONNECTED,
    WEBSOCKET_STATE_STOPPED,
    WEBSOCKET_STATE_STOPPING,
)

from moonraker_api.websockets.websocketclient import ClientAlreadyConnectedError
from .common import create_moonraker_service, create_moonraker_service_looping


async def test_connect(aiohttp_server, moonraker):
    """Test connecting to the websocket server"""
    serv = await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()

    assert moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_CONNECTED

    await moonraker.disconnect()

    assert not moonraker.is_connected
    assert moonraker.state in [WEBSOCKET_STATE_STOPPED, WEBSOCKET_STATE_STOPPING]

    assert moonraker.listener != None
    assert moonraker.listener.state_changed.call_count == 3
    assert moonraker.listener.state_changed.call_args_list[0].args == ("ws_connecting",)
    assert moonraker.listener.state_changed.call_args_list[1].args == ("ws_connected",)
    assert moonraker.listener.state_changed.call_args_list[2].args == ("ws_stopping",)


async def test_connect_twice(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    await create_moonraker_service(aiohttp_server)

    await moonraker.connect()
    with pytest.raises(ClientAlreadyConnectedError):
        await moonraker.connect()
    await moonraker.disconnect()


async def test_api_request(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    await create_moonraker_service(aiohttp_server)

    await moonraker.connect()
    await moonraker.printer_administration.info()
    await moonraker.disconnect()


async def test_api_request_disconnect(aiohttp_server, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service(aiohttp_server, disconnect=True)

    await moonraker.connect()
    with pytest.raises(asyncio.CancelledError):
        await moonraker.printer_administration.info()
    await moonraker.disconnect()


async def test_api_request_timeout(aiohttp_server, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service_looping(aiohttp_server, no_response=True)

    await moonraker.connect()
    with pytest.raises(asyncio.TimeoutError):
        await moonraker.printer_administration.info()
    await moonraker.disconnect()


async def test_api_request_not_connected(aiohttp_server, moonraker):
    """Test sending a request before we are connected to the server"""
    await create_moonraker_service(aiohttp_server)

    with pytest.raises(asyncio.TimeoutError):
        await moonraker.printer_administration.info()
    await moonraker.disconnect()
