# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

"""Moonraker client API tests."""

import asyncio
from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.client_exceptions import ClientConnectionError

from moonraker_api.const import (
    WEBSOCKET_STATE_CONNECTED,
    WEBSOCKET_STATE_STOPPED,
    WEBSOCKET_STATE_STOPPING,
)
from moonraker_api.websockets.websocketclient import (
    ClientAlreadyConnectedError,
    ClientNotAuthenticatedError,
    ClientNotConnectedError,
)

from .common import (
    create_moonraker_service,
    create_moonraker_service_error,
    create_moonraker_service_looping,
)
from .data import (
    TEST_DATA_OBJECTS_QUERY,
    TEST_DATA_SIMPLE_RESPONSE,
    TEST_DATA_SUPPORTED_MODULES,
)


async def test_connect(aiohttp_server, moonraker):
    """Test connecting to the websocket server"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()

    assert moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_CONNECTED

    await moonraker.disconnect()

    assert not moonraker.is_connected
    assert moonraker.state in [WEBSOCKET_STATE_STOPPED, WEBSOCKET_STATE_STOPPING]

    assert moonraker.listener is not None
    assert moonraker.listener.state_changed.call_count == 4
    assert moonraker.listener.state_changed.call_args_list[0].args == ("ws_connecting",)
    assert moonraker.listener.state_changed.call_args_list[1].args == ("ws_connected",)
    assert moonraker.listener.state_changed.call_args_list[2].args == ("ws_stopping",)
    assert moonraker.listener.state_changed.call_args_list[3].args == ("ws_stopped",)


async def test_connect_twice(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    with pytest.raises(ClientAlreadyConnectedError):
        await moonraker.connect()
    assert moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_CONNECTED

    await moonraker.disconnect()
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


async def test_connect_unauthorized(aiohttp_server, moonraker):
    """Test sending a request without authentication"""
    await create_moonraker_service_error(aiohttp_server, web.HTTPUnauthorized())

    with pytest.raises(ClientNotAuthenticatedError):
        connected = await moonraker.connect()
        assert not connected
    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPING

    await moonraker.disconnect()
    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


async def test_api_request(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    await moonraker.get_host_info()
    await moonraker.disconnect()


async def test_api_request_disconnect(aiohttp_server, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service_looping(aiohttp_server, disconnect=True)

    await moonraker.connect()
    with pytest.raises(asyncio.CancelledError):
        await moonraker.get_host_info()
    await moonraker.disconnect()


async def test_api_request_timeout(aiohttp_server, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service_looping(aiohttp_server, no_response=True)

    await moonraker.connect()
    with pytest.raises(asyncio.TimeoutError):
        await moonraker.get_host_info()
    await moonraker.disconnect()


async def test_api_request_not_connected(aiohttp_server, moonraker):
    """Test sending a request before we are connected to the server"""
    await create_moonraker_service_looping(aiohttp_server)

    with pytest.raises(ClientNotConnectedError):
        await moonraker.get_host_info()
    await moonraker.disconnect()

    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED
    assert moonraker.listener is not None
    assert moonraker.listener.state_changed.call_count == 0


@pytest.mark.skip(reason="Not possible to test yet")
async def test_api_send_error(aiohttp_server, moonraker):
    """Test handling error while sending requests"""
    await create_moonraker_service(aiohttp_server)

    with pytest.raises(ClientConnectionError):
        await moonraker.get_host_info()
    await moonraker.disconnect()

    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


@pytest.mark.skip(reason="Not possible to test yet")
async def test_api_recv_error(aiohttp_server, moonraker):
    """Test handling error while receiving requests"""
    await create_moonraker_service(aiohttp_server)

    with patch("AwaitableTask.get_result"):
        with pytest.raises(ClientConnectionError):
            await moonraker.get_host_info()
    await moonraker.disconnect()

    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


async def test_support_modules(aiohttp_server, moonraker):
    """Test getting the supported modules from the API"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    supported_modules = await moonraker.get_supported_modules()
    await moonraker.disconnect()

    assert supported_modules == TEST_DATA_SUPPORTED_MODULES["result"]["objects"]


async def test_service_status(aiohttp_server, moonraker):
    """Test getting the supported modules from the API"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    status = await moonraker.get_klipper_status()
    await moonraker.disconnect()

    assert status == "ready"


@pytest.mark.parametrize(
    "method",
    [
        "printer.restart",
        "printer.emergency_stop",
        "printer.firmware_restart",
    ],
)
async def test_simple_rpc_apis(aiohttp_server, moonraker, method):
    """Test RPC method calls"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    assert moonraker.is_connected
    response = await moonraker.call_method(method)
    await moonraker.disconnect()
    assert not moonraker.is_connected

    assert response is not None
    assert response == TEST_DATA_SIMPLE_RESPONSE["result"]


@pytest.mark.parametrize(
    "method, args",
    [
        (
            "printer.objects.query",
            {"objects": {"gcode_move": None, "toolhead": ["position", "status"]}},
        )
    ],
)
async def test_args_rpc_api(aiohttp_server, moonraker, method, args):
    """Test RPC call with argument passing."""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    assert moonraker.is_connected
    response = await moonraker.call_method(method, **args)

    assert response is not None
    assert response == TEST_DATA_OBJECTS_QUERY["result"]

    await moonraker.disconnect()
    assert not moonraker.is_connected


@pytest.mark.skip(reason="Not implemented yet")
@pytest.mark.parametrize(
    "method",
    ["testing.send_gcode_response"],
)
async def test_subscribe_rpc_api(aiohttp_server, moonraker, method):
    """Test RPC call with argument passing."""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    assert moonraker.is_connected
    response = await moonraker.call_method(method)

    # Subscribe to updates
    assert response is not None
    assert response == TEST_DATA_SIMPLE_RESPONSE["result"]

    # Check that responses are received

    await moonraker.disconnect()
    assert not moonraker.is_connected
