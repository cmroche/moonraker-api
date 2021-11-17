# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
import pytest

from unittest.mock import patch
from .common import create_moonraker_service, create_moonraker_service_looping


async def test_connect(aiohttp_server, moonraker):
    """Test connecting to the websocket server"""
    _ = await create_moonraker_service(aiohttp_server)

    task = asyncio.create_task(moonraker.connect())
    await moonraker.disconnect()
    await task

    # Assert
    assert moonraker.listener != None
    assert moonraker.listener.state_changed.call_count == 1
    assert moonraker.listener.state_changed.call_args.args == ("ws_stopping",)


async def test_api_request(aiohttp_server, aiohttp_client, moonraker):
    """Test sending a request and waiting on a response"""
    await create_moonraker_service(aiohttp_server, no_response=True)

    await moonraker.connect()
    await moonraker.printer_administration.info()
    await moonraker.disconnect()


async def test_api_request_disconnect(aiohttp_server, aiohttp_client, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service(aiohttp_server, disconnect=True)

    await moonraker.connect()
    with pytest.raises(asyncio.CancelledError):
        await moonraker.printer_administration.info()
    await moonraker.disconnect()


async def test_api_request_timeout(aiohttp_server, aiohttp_client, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service_looping(aiohttp_server, no_response=True)

    await moonraker.connect()
    with pytest.raises(asyncio.TimeoutError):
        await moonraker.printer_administration.info()
    await moonraker.disconnect()


async def test_api_request_not_connected(aiohttp_server, aiohttp_client, moonraker):
    """Test sending a request before we are connected to the server"""
    await create_moonraker_service(aiohttp_server)

    await moonraker.connect()
    await moonraker.printer_administration.info()
    await moonraker.disconnect()
