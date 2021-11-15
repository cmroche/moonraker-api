# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio

from aiohttp import web
from pytest_aiohttp import aiohttp_server
from random import randint

from moonraker_api import MoonrakerClient, MoonrakerListener, PrinterAdminstration
from .common import create_moonraker_service
from .data import TEST_DATA_SUPPORTED_MODULES


async def test_connect(aiohttp_server, moonraker):
    """Test connecting to the websocket server"""
    server = await create_moonraker_service(aiohttp_server)

    task = asyncio.create_task(moonraker.connect())
    await moonraker.disconnect()
    await task

    # Assert
    assert moonraker.listener != None
    assert moonraker.listener.state_changed.call_count == 1
    assert moonraker.listener.state_changed.call_args.args == ("ws_stopping",)


async def test_api_request(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    server = await create_moonraker_service(aiohttp_server)

    task = asyncio.create_task(moonraker.connect())
    response = await moonraker.printer_administration.restart()
    await moonraker.disconnect()
    await task
