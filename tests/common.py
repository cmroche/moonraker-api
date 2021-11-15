# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license
import json
from aiohttp import web, WSMsgType
from pytest_aiohttp import aiohttp_server

from tests.data import TEST_DATA_UPDATE, TEST_METHOD_RESPONSES


async def create_moonraker_service(aiohttp_server):
    """Create a fake websocket server to handle API requests"""

    async def ws_handler(request: web.Request) -> web.Response:
        """Mock websocket request handler for testing"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        ws.send_str(json.dumps(TEST_DATA_UPDATE))

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
                    break

                obj = msg.json()
                method = obj.get("method")
                if method in TEST_METHOD_RESPONSES:
                    ws.send_json(TEST_METHOD_RESPONSES[method])
            elif msg.type == WSMsgType.ERROR:
                print("ws connection closed with exception %s", ws.exception())

        return ws

    app = web.Application()
    app.router.add_get("/websocket", ws_handler)
    return await aiohttp_server(app, port=7125)
