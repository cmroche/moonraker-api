# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
from random import randint

from pytest_aiohttp import aiohttp_server

from .common import create_moonraker_service_looping
from .data import TEST_DATA_SUPPORTED_MODULES


async def test_support_modules(aiohttp_server, moonraker):
    """Test getting the supported modules from the API"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    await asyncio.sleep(2)  # Command is exeptionally auto-propagated
    await moonraker.disconnect()

    assert (
        moonraker.printer_administration.supported_modules
        == TEST_DATA_SUPPORTED_MODULES["result"]["objects"]
    )


async def test_printer_info(aiohttp_server, moonraker):
    """Test ``printer.info`` method calls"""
