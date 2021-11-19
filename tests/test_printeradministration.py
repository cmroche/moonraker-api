# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
from typing import get_type_hints
import pytest
from random import randint

from pytest_aiohttp import aiohttp_server

from .common import create_moonraker_service, create_moonraker_service_looping
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


@pytest.mark.parametrize(
    "method", ["host_restart", "info", "emergency_stop", "firmware_restart"]
)
async def test_simple_rpc_apis(aiohttp_server, moonraker, method):
    """Test RPC method calls"""
    await create_moonraker_service(aiohttp_server)

    await moonraker.connect()
    assert moonraker.is_connected
    func = getattr(moonraker.printer_administration, method)
    response = await func()
    await moonraker.disconnect()
    assert not moonraker.is_connected

    assert response is not None
