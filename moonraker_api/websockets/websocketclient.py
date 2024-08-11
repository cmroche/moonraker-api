# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license
"""Websocket management."""

from __future__ import annotations

import asyncio
import json
import logging
from asyncio import Task
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from asyncio.tasks import FIRST_COMPLETED
from random import randint
from typing import Any, Coroutine

import aiohttp
from aiohttp import ClientConnectionError, ClientResponseError, ClientSession, WSMsgType
from aiohttp.client_ws import ClientWebSocketResponse
from async_timeout import timeout as async_timeout

from moonraker_api.const import (
    WEBSOCKET_CONNECTION_TIMEOUT,
    WEBSOCKET_STATE_CONNECTED,
    WEBSOCKET_STATE_CONNECTING,
    WEBSOCKET_STATE_STOPPED,
    WEBSOCKET_STATE_STOPPING,
)
from moonraker_api.websockets.awaitabletask import AwaitableTask, AwaitableTaskContext

_LOGGER = logging.getLogger(__name__)


class WebsocketStatusListener:
    """Base lass providing functions to receive events from the
    moonraker API"""

    async def state_changed(self, state: str) -> None:
        """Called when the websocket state changes"""

    async def on_exception(self, exception: type | BaseException) -> None:
        """Called when an exception arises from the websocket run loop"""

    async def on_notification(self, method: str, data: Any) -> None:
        """Called when a notification is sent"""


class WebsocketRequest(AwaitableTask):
    """Make a waitable request to the API"""

    def __init__(
        self,
        req_id: int,
        request: Any,
        timeout: int = WEBSOCKET_CONNECTION_TIMEOUT,
        loop: AbstractEventLoop = None,
    ) -> None:
        """Initialize the request"""
        super().__init__(req_id, timeout, loop)
        self.request = request


class ClientAlreadyConnectedError(Exception):
    """Raised when trying to connect to an already active connection"""


class ClientNotConnectedError(Exception):
    """Raised when trying to make a request without a connection"""


class ClientNotAuthenticatedError(Exception):
    """Raised when trying to connect without correct authentication"""


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
        api_key: str | None = None,
        ssl: bool = False,
        loop: AbstractEventLoop = None,
        timeout: int = WEBSOCKET_CONNECTION_TIMEOUT,
        session: aiohttp.ClientSession = None,
    ) -> None:
        """Initialize the moonraker client object

        Args:
            listener (MoonrakerListen): Event listener
            host (str): hostname or IP address of the printer
            port (int, optional): Defaults to 7125
            api_key (str, options): API key
            loop (AbstractEventLoop, option):
                Provide an optional asyncio loop for tasks
        """
        self.listener = listener or WebsocketStatusListener()
        self.host = host
        self.port = port
        self.api_key = api_key
        self.ssl = ssl
        self._timeout = timeout
        self.session = session
        self._loop = loop or asyncio.get_event_loop_policy().get_event_loop()

        self._ws = None

        self._task = None
        self._state = WEBSOCKET_STATE_STOPPED
        self._retries = 0
        self._tasks = []

        self._runtask: Task = None
        self._requests_pending = asyncio.Queue()
        self._requests: dict[int, WebsocketRequest] = {}

    def _task_done_callback(self, task) -> None:
        try:
            task.exception()
        except Exception as error:
            _LOGGER.exception("Uncaught exception", exc_info=error)
        self._tasks.remove(task)

    def _create_task(self, coro) -> Task:
        task = self._loop.create_task(coro)
        self._tasks.append(task)
        task.add_done_callback(self._task_done_callback)
        return task

    @property
    def tasks(self) -> list[Coroutine]:
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
        if self._state != value:
            self._state = value
            _LOGGER.debug("Websocket changing to state %s", value)
            self._create_task(self.listener.state_changed(value))

    def _build_websocket_uri(self) -> str:
        protocol = "wss://" if self.ssl else "ws://"
        return f"{protocol}{self.host}:{self.port}/websocket"

    def _get_next_tx_id(self) -> int:
        return randint(1, 999999)

    def _build_websocket_request(self, method: str, **kwargs: Any) -> tuple[int, Any]:
        tx_id = self._get_next_tx_id()
        req = {"jsonrpc": "2.0", "method": method, "id": tx_id}
        if kwargs:
            req["params"] = kwargs
        return tx_id, req

    @property
    def is_connected(self) -> bool:
        """Return True when the websocket is connected"""
        return self.state == WEBSOCKET_STATE_CONNECTED

    async def _request(self, method: str, **kwargs: Any) -> WebsocketRequest:
        req_id, data = self._build_websocket_request(method, **kwargs)
        req = WebsocketRequest(req_id, data, timeout=self._timeout, loop=self._loop)
        await self._requests_pending.put(req)
        return req

    def request(
        self, method: str, **kwargs: Any
    ) -> AwaitableTaskContext[WebsocketRequest]:
        """Build a json-rpc request for the API

        Args:
            method (str): The api method to call
            **kwargs: Arguments to pass to the API call
        """
        if not self.is_connected:
            raise ClientNotConnectedError()

        return AwaitableTaskContext[WebsocketRequest](
            self._request(method, **kwargs), self._requests
        )

    async def _loop_recv_internal(self, message: Any) -> None:
        """Private method to allow processing if incoming messages"""

    async def loop_recv(self, client: ClientWebSocketResponse) -> None:
        """Run the websocket connection and process send/receive
        of messages"""
        async for message in client:
            _LOGGER.debug("Received message: %s", message)
            if message.type == WSMsgType.TEXT:
                msgobj = message.json()

                # Look for incoming RPC responses, and match to
                # their outstanding tasks
                res_id = msgobj.get("id")
                if res_id:
                    req = self._requests.get(res_id)
                    if req and "result" in msgobj:
                        req.set_result(msgobj["result"])
                    elif req and "error" in msgobj:
                        req.set_result({"error": msgobj["error"]})

                # Dispatch messages to modules
                if await self._loop_recv_internal(msgobj):
                    continue

                # Finally, dispatch notifications
                if msgobj.get("method"):
                    method = msgobj["method"]
                    params = msgobj.get("params")
                    self._create_task(self.listener.on_notification(method, params))

            elif message.type == WSMsgType.CLOSED:
                _LOGGER.info("Received websocket connection gracefully closed message")
                break
            elif message.type == WSMsgType.ERROR:
                _LOGGER.info("Received websocket connection error message")
                break

    async def loop_send(self, client: ClientWebSocketResponse) -> None:
        """Run the websocket request queue"""
        while self.state not in [WEBSOCKET_STATE_STOPPING, WEBSOCKET_STATE_STOPPED]:
            request = await self._requests_pending.get()

            try:
                request_str = json.dumps(request.request)
                _LOGGER.debug("Sending message %s", request_str)
                await client.send_str(request_str)
            except Exception as error:  # pylint: disable=broad-except
                request.set_exception(error)
                raise error
            finally:
                self._requests_pending.task_done()

    async def _run(self, conn_event: Future) -> None:
        """Start the websocket connection and run the update loop.

        Args:
            conn_event (Event): This event is set once the connection is complete
        """
        if not self.session:
            self.session = ClientSession(loop=self._loop)

        async def set_exception(exception: BaseException) -> None:
            """Sets an exception received by the run loop"""
            if not conn_event.done():
                conn_event.set_exception(exception)
            for req in self._requests.values():
                if not req.done():
                    req.set_exception(exception)
            await self._create_task(self.listener.on_exception(exception))

        if self.state != WEBSOCKET_STATE_STOPPED:
            self.state = WEBSOCKET_STATE_CONNECTING
            try:
                headers = None
                if self.api_key:
                    headers = [("X-Api-Key", self.api_key)]
                async with self.session.ws_connect(
                    self._build_websocket_uri(),
                    headers=headers,
                    receive_timeout=self._timeout,
                    autoping=True,
                    heartbeat=self._timeout / 3,
                ) as websocket:
                    self._ws = websocket
                    self.state = WEBSOCKET_STATE_CONNECTED
                    conn_event.set_result(True)

                    # Start the send/recv routines
                    done, unfinished = await asyncio.wait(
                        (
                            self._loop.create_task(self.loop_recv(websocket)),
                            self._loop.create_task(self.loop_send(websocket)),
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
                if error.status == 401:
                    _LOGGER.error("API access is unauthorized")
                    self.state = WEBSOCKET_STATE_STOPPING
                    await set_exception(ClientNotAuthenticatedError)
                else:
                    await set_exception(error)
            except ClientConnectionError as error:
                await set_exception(error)

                _LOGGER.error("Websocket connection error: %s", error)
            except asyncio.TimeoutError as error:
                await set_exception(error)
                _LOGGER.error("Websocket connection timed out")
            except Exception as error:  # pylint: disable=broad-except
                await set_exception(error)
                _LOGGER.error("Websocket unknown error: %s", error)
            finally:
                # Clean up pending requests
                for _ in range(self._requests_pending.qsize()):
                    self._requests_pending.get_nowait()
                    self._requests_pending.task_done()
                for req in self._requests.values():
                    req.cancel()
                self.state = WEBSOCKET_STATE_STOPPED

    async def connect(self) -> bool:
        """Start the run loop and connect

        Returns:
            A ``boolean`` indicating if the connection succeeded.
        """
        if self._runtask and not self._runtask.done():
            raise ClientAlreadyConnectedError()

        self.state = WEBSOCKET_STATE_CONNECTING
        conn_event = self._loop.create_future()
        self._runtask = self._loop.create_task(self._run(conn_event))
        await asyncio.wait_for(conn_event, self._timeout)

        return self.is_connected

    async def disconnect(self) -> None:
        """Stop the websocket connection."""
        if self.state != WEBSOCKET_STATE_STOPPED:
            self.state = WEBSOCKET_STATE_STOPPING
        if self._ws:
            await self._ws.close()
        if self._runtask:
            await self._runtask
