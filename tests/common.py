# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license
import json

from aiohttp import WSMsgType, web
from aiohttp.web_exceptions import HTTPClientError
from pytest_aiohttp.plugin import aiohttp_server

from tests.data import TEST_METHOD_RESPONSES


async def create_moonraker_service(aiohttp_server, disconnect: bool = False):
    """Create a fake websocket server to handle API requests

    Args:
        disconnect (bool, optional): Close the websocket immediately
        instead of responding to the request
    """


async def create_moonraker_service_looping(
    aiohttp_server, disconnect: bool = False, no_response: bool = False
):
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
                if disconnect and method not in ["printer.objects.list", "server.info"]:
                    await ws.close()
                    break
                elif no_response and method not in [
                    "printer.objects.list",
                    "server.info",
                ]:
                    continue
                elif method in TEST_METHOD_RESPONSES:
                    req_id = obj.get("id")
                    response = TEST_METHOD_RESPONSES[method]
                    response["id"] = req_id
                    resp = json.dumps(response)
                    await ws.send_str(resp)
            elif msg.type == WSMsgType.ERROR:
                print("ws connection closed with exception %s", ws.exception())

        return ws

    app = web.Application()
    app.router.add_get("/websocket", ws_handler)
    return await aiohttp_server(app, port=7125)


async def create_moonraker_service_error(aiohttp_server, client_error: HTTPClientError):
    """Create a fake websocket server to handle API requests

    Args:
        disconnect (bool, optional): Close the websocket immediately
        instead of responding to the request
    """

    async def ws_handler(request: web.Request) -> web.Response:
        """Mock websocket request handler for testing"""
        return client_error

    app = web.Application()
    app.router.add_get("/websocket", ws_handler)
    return await aiohttp_server(app, port=7125)
