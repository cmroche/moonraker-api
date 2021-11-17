# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license
import json
from aiohttp import web, WSMsgType
from pytest_aiohttp import aiohttp_client, aiohttp_server

from tests.data import TEST_METHOD_RESPONSES


async def create_moonraker_service(aiohttp_server, disconnect: bool = False):
    """Create a fake websocket server to handle API requests

    Args:
        disconnect (bool, optional): Close the websocket immediately
        instead of responding to the request
    """

    async def ws_handler(request: web.Request) -> web.Response:
        """Mock websocket request handler for testing"""
        ws = web.WebSocketResponse()
        if not ws.can_prepare(request):
            return web.HTTPUpgradeRequired()

        await ws.prepare(request)
        msg = await ws.receive()

        if msg.type == WSMsgType.TEXT:
            obj = msg.json()
            method = obj.get("method")
            if not disconnect and method in TEST_METHOD_RESPONSES:
                resp = json.dumps(TEST_METHOD_RESPONSES[method])
                await ws.send_str(resp)

        await ws.close()
        return ws

    app = web.Application()
    app.router.add_get("/websocket", ws_handler)
    return await aiohttp_server(app, port=7125)


async def create_moonraker_service_looping(aiohttp_server, no_response: bool = False):
    """Create a fake websocket server to handle API requests

    Args:
        no_response (bool, optional): Don't respond to incoming requests
    """

    async def ws_handler(request: web.Request) -> web.Response:
        """Mock websocket request handler for testing"""
        ws = web.WebSocketResponse()
        if not ws.can_prepare(request):
            return web.HTTPUpgradeRequired()

        await ws.prepare(request)

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
                    break

                obj = msg.json()
                method = obj.get("method")
                if not no_response and method in TEST_METHOD_RESPONSES:
                    resp = json.dumps(TEST_METHOD_RESPONSES[method])
                    await ws.send_str(resp)
            elif msg.type == WSMsgType.ERROR:
                print("ws connection closed with exception %s", ws.exception())

        return ws

    app = web.Application()
    app.router.add_get("/websocket", ws_handler)
    return await aiohttp_server(app, port=7125)
