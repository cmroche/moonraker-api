# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

"""Moonraker client API tests."""

import asyncio
from json import JSONDecodeError
from unittest.mock import Mock, patch

import pytest
from aiohttp import ClientSession, ClientWebSocketResponse, web
from aiohttp.client_exceptions import ClientConnectionError

from moonraker_api.const import (
    WEBSOCKET_STATE_CONNECTED,
    WEBSOCKET_STATE_STOPPED,
    WEBSOCKET_STATE_STOPPING,
)
from moonraker_api.moonrakerclient import MoonrakerClient, MoonrakerListener
from moonraker_api.websockets.websocketclient import (
    ClientAlreadyConnectedError,
    ClientNotAuthenticatedError,
    ClientNotConnectedError,
)

from .common import (
    create_moonraker_service_error,
    create_moonraker_service_looping,
)
from .data import (
    TEST_DATA_OBJECTS_QUERY,
    TEST_DATA_SIMPLE_RESPONSE,
    TEST_DATA_SUPPORTED_MODULES,
)


@pytest.mark.parametrize(
    ("route_prefix", "expected_uri"),
    [
        (None, "ws://127.0.0.1:7125/websocket"),
        ("", "ws://127.0.0.1:7125/websocket"),
        ("/", "ws://127.0.0.1:7125/websocket"),
        ("moonraker", "ws://127.0.0.1:7125/moonraker/websocket"),
        ("/moonraker", "ws://127.0.0.1:7125/moonraker/websocket"),
        ("moonraker/", "ws://127.0.0.1:7125/moonraker/websocket"),
        ("/moonraker/", "ws://127.0.0.1:7125/moonraker/websocket"),
        (
            "moonraker/printer1",
            "ws://127.0.0.1:7125/moonraker/printer1/websocket",
        ),
        (
            "/moonraker/printer1/",
            "ws://127.0.0.1:7125/moonraker/printer1/websocket",
        ),
    ],
)
async def test_build_websocket_uri_normalizes_route_prefix(route_prefix, expected_uri):
    """Test websocket URI route prefix creation and slash normalization."""
    listener = Mock(name="MoonrakeListener", spec=MoonrakerListener)
    moonraker = MoonrakerClient(
        host="127.0.0.1",
        port=7125,
        listener=listener,
        route_prefix=route_prefix,
        loop=asyncio.get_running_loop(),
    )

    assert moonraker._build_websocket_uri() == expected_uri


async def test_connect(aiohttp_server, moonraker):
    """Test connecting to the websocket server"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()

    session = moonraker.session
    assert moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_CONNECTED

    await moonraker.disconnect()
    assert session.closed

    assert not moonraker.is_connected
    assert moonraker.state in [WEBSOCKET_STATE_STOPPED, WEBSOCKET_STATE_STOPPING]

    assert moonraker.listener is not None
    assert moonraker.listener.state_changed.call_count == 4
    assert moonraker.listener.state_changed.call_args_list[0].args == ("ws_connecting",)
    assert moonraker.listener.state_changed.call_args_list[1].args == ("ws_connected",)
    assert moonraker.listener.state_changed.call_args_list[2].args == ("ws_stopping",)
    assert moonraker.listener.state_changed.call_args_list[3].args == ("ws_stopped",)


async def test_reconnect_with_shared_session(aiohttp_server):
    await create_moonraker_service_looping(aiohttp_server)
    async with ClientSession() as session:
        client = MoonrakerClient(None, "127.0.0.1", session=session)
        for _ in range(2):
            await client.connect()
            assert await client.get_klipper_status() == "ready"
            await client.disconnect()
            assert not session.closed


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

    session = moonraker.session
    await moonraker.disconnect()
    assert session.closed
    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


async def test_api_request(aiohttp_server, moonraker):
    """Test sending a request and waiting on a response"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    async with moonraker.request("printer.info") as first:
        async with moonraker.request("server.info") as second:
            assert second.req_id > first.req_id
            assert (await second.get_result())["klippy_state"] == "ready"
            assert "state_message" in await first.get_result()
    await moonraker.disconnect()


async def test_api_request_disconnect(aiohttp_server, moonraker):
    """Test server hangup after request"""
    await create_moonraker_service_looping(aiohttp_server, disconnect=True)

    await moonraker.connect()
    session = moonraker.session
    with pytest.raises(asyncio.CancelledError):
        await moonraker.get_host_info()
    await moonraker.disconnect()
    assert session.closed

    await moonraker.connect()
    assert await moonraker.get_klipper_status() == "ready"
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


async def test_api_send_error(aiohttp_server, moonraker):
    await create_moonraker_service_looping(aiohttp_server, no_response=True)
    await moonraker.connect()
    error = ClientConnectionError("connection lost")
    async with moonraker.request("printer.info") as pending:
        # A successful round trip ensures the earlier request was already sent.
        assert await moonraker.get_klipper_status() == "ready"
        with patch.object(ClientWebSocketResponse, "send_str", side_effect=error):
            with pytest.raises(ClientConnectionError) as sending:
                await moonraker.get_host_info()
        with pytest.raises(ClientConnectionError) as waiting:
            await pending.get_result()
    await moonraker.disconnect()
    assert sending.value is waiting.value is error
    moonraker.listener.on_exception.assert_awaited_once_with(error)

    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


async def test_api_recv_error(aiohttp_server, moonraker):
    """A later reply succeeds even if the next frame fails an earlier request."""
    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.receive_json()
        second = await ws.receive_json()
        await ws.send_json({"jsonrpc": "2.0", "id": second["id"], "result": "ok"})
        await ws.send_str("not JSON")
        return ws

    app = web.Application()
    app.router.add_get("/websocket", handler)
    await aiohttp_server(app, port=moonraker.port)
    await moonraker.connect()
    async with moonraker.request("printer.info") as first:
        async with moonraker.request("server.info") as second:
            assert await second.get_result() == "ok"
            with pytest.raises(JSONDecodeError) as failure:
                await first.get_result()
    await moonraker.disconnect()
    moonraker.listener.on_exception.assert_awaited_once_with(failure.value)

    assert not moonraker.is_connected
    assert moonraker.state == WEBSOCKET_STATE_STOPPED


async def test_support_modules(aiohttp_server, moonraker):
    """Test getting the supported modules from the API"""
    await create_moonraker_service_looping(aiohttp_server)

    await moonraker.connect()
    supported_modules = await moonraker.get_supported_modules()
    await moonraker.disconnect()

    assert supported_modules == TEST_DATA_SUPPORTED_MODULES["result"]["objects"]


async def test_temperature_sensors_live_updates(aiohttp_server, moonraker):
    chamber = "temperature_sensor chamber_top"
    monitor = "tmc2240 stepper_x"
    status = {
        "print_stats": {"state": "printing"},
        "extruder": {"target": 210.0, "temperature": 209.5},
        "heater_bed": {"temperature": 60.0},
        chamber: {"temperature": 62.1},
        monitor: {"temperature": None},
    }
    delta = [{chamber: {"temperature": 0.0}}, 123.0]

    async def handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        discovery = await ws.receive_json()
        assert discovery["method"] == "printer.objects.query"
        assert discovery["params"] == {
            "objects": {"heaters": ["available_sensors", "available_monitors"]},
        }
        await ws.send_json({
            "jsonrpc": "2.0",
            "id": discovery["id"],
            "result": {"status": {"heaters": {
                "available_sensors": ["extruder", "heater_bed", chamber],
                "available_monitors": [monitor, "extruder"],
            }}},
        })
        subscription = await ws.receive_json()
        assert subscription["method"] == "printer.objects.subscribe"
        assert subscription["params"] == {"objects": {
            "print_stats": None,
            "extruder": ["target", "temperature"],
            "heater_bed": ["temperature"],
            chamber: ["temperature"],
            monitor: ["temperature"],
        }}
        await ws.send_json({
            "jsonrpc": "2.0", "id": subscription["id"], "result": {"status": status},
        })
        await ws.send_json({
            "jsonrpc": "2.0", "method": "notify_status_update", "params": delta,
        })
        await ws.receive()  # Keep the connection open until the client disconnects.
        return ws

    notified = asyncio.Event()
    moonraker.listener.on_notification.side_effect = lambda *_: notified.set()
    app = web.Application()
    app.router.add_get("/websocket", handler)
    server = await aiohttp_server(app)
    moonraker.port = server.port
    await moonraker.connect()
    try:
        names = await moonraker.get_temperature_sensors()
        assert names == ["extruder", "heater_bed", chamber, monitor]
        objects = {"print_stats": None, "extruder": ["target"]}
        for name in names:
            objects.setdefault(name, []).append("temperature")
        response = await moonraker.call_method("printer.objects.subscribe", objects=objects)
        assert {name: response["status"][name]["temperature"] for name in names} == {
            "extruder": 209.5, "heater_bed": 60.0, chamber: 62.1, monitor: None,
        }
        await asyncio.wait_for(notified.wait(), timeout=2)
        moonraker.listener.on_notification.assert_awaited_once_with("notify_status_update", delta)
    finally:
        await moonraker.disconnect()


@pytest.mark.parametrize(("response", "expected"), [
    ({"status": {"heaters": {"available_sensors": ["extruder"]}}}, ["extruder"]),
    ({"status": {"heaters": {"available_monitors": None}}}, []),
    ({"status": {}}, []),
    ({"status": {"heaters": {"available_sensors": [], "available_monitors": []}}}, []),
    ({"error": {"code": -32601, "message": "Klipper unavailable"}}, None),
])
async def test_temperature_sensors_discovery_results(moonraker, response, expected):
    with patch.object(moonraker, "call_method", return_value=response):
        assert await moonraker.get_temperature_sensors() == expected


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
