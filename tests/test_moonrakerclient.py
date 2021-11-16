# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio

from .common import create_moonraker_service


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


async def test_api_request(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    _ = await create_moonraker_service(aiohttp_server)

    task = asyncio.create_task(moonraker.connect())
    # TODO: This doesn't work because we don't handle server responses yet
    # it just times out ...
    response = await moonraker.printer_administration.restart()
    await moonraker.disconnect()
    await task
