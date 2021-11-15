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


async def test_support_modules(aiohttp_server, moonraker):
    """Test getting the supported modules from the API"""
    server = await create_moonraker_service(aiohttp_server)

    task = asyncio.create_task(moonraker.connect())
    await moonraker.disconnect()
    await task

    assert (
        moonraker.printer_administration.supported_modules
        == TEST_DATA_SUPPORTED_MODULES["objects"]
    )
