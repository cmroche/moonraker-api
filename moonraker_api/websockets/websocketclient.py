# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
from asyncio.tasks import FIRST_COMPLETED
import logging
import json

from aiohttp import ClientSession, ClientResponseError, ClientConnectionError, WSMsgType
from asyncio import Task
from asyncio.events import AbstractEventLoop
from typing import Any, Coroutine, Dict, List

from aiohttp.client_ws import ClientWebSocketResponse

from moonraker_api.const import (
    WEBSOCKET_RETRY_DELAY,
    WEBSOCKET_STATE_CONNECTED,
    WEBSOCKET_STATE_CONNECTING,
    WEBSOCKET_STATE_DISCONNECTED,
    WEBSOCKET_STATE_READY,
    WEBSOCKET_STATE_STOPPING,
    WEBSOCKET_STATE_STOPPED,
)
from moonraker_api.websockets.awaitabletask import AwaitableTask, AwaitableTaskContext

_LOGGER = logging.getLogger(__name__)


class WebsocketStatusListener:
    """Base lass providing functions to receive events from the
    moonraker API"""

    async def state_changed(self, state: str) -> None:
        """Called when the websocket state changes"""


class WebsocketRequest(AwaitableTask):
    """Make a waitable request to the API"""

    def __init__(self, req_id: int, request: Any, timeout: int = 120) -> None:
        """Initialize the request"""
        super().__init__(req_id, timeout)
        self.response = None
        self.request = request

    async def result(self):
        """Get the awaitable response, up to the timeout"""
        await self.wait()
        return self.response

    def set_result(self, response: Any):
        """Set the response and signal that we are done"""
        self.response = response
        self.set_complete()


class WebsocketClient:
    """Moonraker API client class, repesents an API instance

    Attributes:
      host: hostname or IP address of the printer
      port: Defaults to 7125
    """

    def __init__(
        self,
        listener: WebsocketStatusListener,
        host: str,
        port: int = 7125,
        loop: AbstractEventLoop = None,
    ) -> None:
        """Initialize the moonraker client object

        Args:
            listener (MoonrakerListen): Event listener
            host (str): hostname or IP address of the printer
            port (int, optional): Defaults to 7125
            loop (AbstractEventLoop, option):
                Provide an optional asyncio loop for tasks
        """
        self.listener = listener or WebsocketStatusListener()
        self.host = host
        self.port = port
        self._loop = loop or asyncio.get_event_loop_policy().get_event_loop()

        self._ws = None

        self._task = None
        self._state = None
        self._retries = 0
        self._tasks = []
        self._req_id = 0

        self._requests_pending = asyncio.Queue[WebsocketRequest]()
        self._requests: Dict[int, AwaitableTask] = {}

    def _task_done_callback(self, task):
        if task.exception():
            _LOGGER.exception("Uncaught exception", exc_info=task.exception())
        self._tasks.remove(task)

    def _create_task(self, coro) -> Task:
        task = self._loop.create_task(coro)
        self._tasks.append(task)
        task.add_done_callback(self._task_done_callback)
        return task

    @property
    def tasks(self) -> List[Coroutine]:
        """Returns the outstanding tasks waiting completion."""
        return self._tasks

    @property
    def state(self) -> str:
        """Return the current state of the websocket

        Returns:
            str: Connection state, from ``WEBSOCKET_STATE_*``
        """
        return self._state

    @state.setter
    def state(self, value: str) -> None:
        """Sets the current state of the websocket and raises a
        state change event."""
        self._state = value
        _LOGGER.debug("Websocket changing to state %s", value)
        self._create_task(self.listener.state_changed(value))

    def _build_websocket_uri(self) -> str:
        return f"ws://{self.host}:{self.port}/websocket"

    def _get_next_tx_id(self) -> int:
        tx_id = self._req_id
        self._req_id += 1
        return tx_id

    def _build_websocket_request(self, method: str, **kwargs) -> Any:
        tx_id = self._get_next_tx_id()
        req = {"jsonrpc": "2.0", "method": method, "id": tx_id}
        if kwargs:
            req["params"] = kwargs
        return tx_id, req

    async def _request(self, method: str, **kwargs) -> Any:
        req_id, data = self._build_websocket_request(method, **kwargs)
        req = WebsocketRequest(req_id, data)
        await self._requests_pending.put(req)
        return req

    async def request(self, method: str, **kwargs) -> Any:
        """Build a json-rpc request for the API

        Args:
            method (str): The api method to call
            **kwargs: Arguments to pass to the API call
        """
        return AwaitableTaskContext[WebsocketRequest](
            self._request(method, **kwargs), self._requests
        )

    async def _loop_recv_internal(self, message) -> None:
        """Private method to allow processing if incoming messages"""

    async def loop_recv(self, client: ClientWebSocketResponse) -> None:
        """Run the websocket connection and process send/receive
        of messages"""
        async for message in client:
            _LOGGER.debug("Received message: %s", message)
            if message.type == WSMsgType.TEXT:
                m = message.json()
                await self._loop_recv_internal(m)

                if self.state == WEBSOCKET_STATE_CONNECTED:
                    if m.has("objects"):
                        self.state = WEBSOCKET_STATE_READY

            elif message.type == WSMsgType.CLOSED:
                _LOGGER.info("Recived websocket connection gracefully closed message")
                break
            elif message.type == WSMsgType.ERROR:
                _LOGGER.info("Received websocket connection error message")
                break

    async def loop_send(self, client: ClientWebSocketResponse) -> None:
        """Run the websocket request queue"""
        while self.state not in [WEBSOCKET_STATE_STOPPED, WEBSOCKET_STATE_DISCONNECTED]:
            request = await self._requests_pending.get()
            request_str = json.dumps(request.request)
            _LOGGER.debug("Sending message %s", request_str)
            await client.send_str(request_str)
            self._requests_pending.task_done()

    async def connect(self):
        """Start the websocket connection."""
        session = ClientSession()

        while self.state != WEBSOCKET_STATE_STOPPING:
            self.state = WEBSOCKET_STATE_CONNECTING
            try:
                async with session.ws_connect(self._build_websocket_uri()) as ws:
                    self.state = WEBSOCKET_STATE_CONNECTED
                    ws.send_json(self._build_websocket_request("printer.objects.list"))
                    done, unfinished = await asyncio.wait(
                        (
                            self._loop.create_task(self.loop_recv(ws)),
                            self._loop.create_task(self.loop_send(ws)),
                        ),
                        return_when=FIRST_COMPLETED,
                    )

                    for task in unfinished:
                        task.cancel()

                    # Raise exceptions
                    (future,) = done
                    future.result()

            except ClientResponseError as error:
                _LOGGER.warning("Websocket request error: %s", error)
            except ClientConnectionError as error:
                _LOGGER.error("Websocket connection error: %s", error)
            except asyncio.TimeoutError:
                _LOGGER.error("Websocket connection timed out")
            except Exception as error:  # pylint: disable=broad-except
                _LOGGER.error("Websocket unknown error: %s", error)

            # Stop was requested, do not try to reconnect
            if self.state == WEBSOCKET_STATE_STOPPING:
                self.state = WEBSOCKET_STATE_STOPPED
                break
            else:
                self.state = WEBSOCKET_STATE_DISCONNECTED
                await asyncio.sleep(WEBSOCKET_RETRY_DELAY)

    async def disconnect(self):
        """Stop the websocket connection."""
        self.state = WEBSOCKET_STATE_STOPPING
        if self._ws:
            await self._ws.close()
