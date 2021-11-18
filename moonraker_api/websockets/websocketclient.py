# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import asyncio
from asyncio.futures import Future
from asyncio.tasks import FIRST_COMPLETED
import logging
import json
import traceback

from aiohttp import ClientSession, ClientResponseError, ClientConnectionError, WSMsgType
from asyncio import Task
from asyncio.events import AbstractEventLoop
from typing import Any, Coroutine, Dict, List

from aiohttp.client_ws import ClientWebSocketResponse
from asyncio.locks import Event

from moonraker_api.const import (
    WEBSOCKET_CONNECTION_TIMEOUT,
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

    def __init__(
        self, req_id: int, request: Any, timeout: int = WEBSOCKET_CONNECTION_TIMEOUT
    ) -> None:
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
        api_key: str = None,
        retry: bool = True,
        loop: AbstractEventLoop = None,
        timeout: int = WEBSOCKET_CONNECTION_TIMEOUT,
    ) -> None:
        """Initialize the moonraker client object

        Args:
            listener (MoonrakerListen): Event listener
            host (str): hostname or IP address of the printer
            port (int, optional): Defaults to 7125
            api_key (str, options): API key
            retry (bool, optional): Enable reconnectry/retry on error
            loop (AbstractEventLoop, option):
                Provide an optional asyncio loop for tasks
        """
        self.listener = listener or WebsocketStatusListener()
        self.host = host
        self.port = port
        self.retry = retry
        self.api_key = api_key
        self._timeout = timeout
        self._loop = loop or asyncio.get_event_loop_policy().get_event_loop()

        self._ws = None

        self._task = None
        self._state = WEBSOCKET_STATE_STOPPED
        self._retries = 0
        self._tasks = []
        self._req_id = 0

        self._runtask: Task = None
        self._requests_pending = asyncio.Queue[WebsocketRequest]()
        self._requests: Dict[int, WebsocketRequest] = {}

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

    @property
    def is_connected(self):
        """Return True when the websocket is connected"""
        return self.state in [WEBSOCKET_STATE_CONNECTED, WEBSOCKET_STATE_READY]

    async def _request(self, method: str, **kwargs) -> Any:
        req_id, data = self._build_websocket_request(method, **kwargs)
        req = WebsocketRequest(req_id, data, timeout=self._timeout)
        await self._requests_pending.put(req)
        return req

    def request(self, method: str, **kwargs) -> Any:
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

    async def _loop_recv_internal(self, message) -> None:
        """Private method to allow processing if incoming messages"""

    async def loop_recv(self, client: ClientWebSocketResponse) -> None:
        """Run the websocket connection and process send/receive
        of messages"""
        async for message in client:
            _LOGGER.debug("Received message: %s", message)
            if message.type == WSMsgType.TEXT:
                m = message.json()

                # Look for incoming RPC responses, and match to
                # their outstanding tasks
                if m.get("result"):
                    res_id = m.get("id")
                    if res_id:
                        req = self._requests.get(res_id)
                        if req:
                            req.set_result(m["result"])
                    if self.state == WEBSOCKET_STATE_CONNECTED:
                        if m["result"].get("objects"):
                            self.state = WEBSOCKET_STATE_READY

                # Dispatch messages to modules
                await self._loop_recv_internal(m)

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

    async def _run(self, conn_event: Future):
        """Start the websocket connection and run the update loop.

        Args:
            conn_event (Event): This event is set once the connection is complete
        """
        session = ClientSession()

        while self.state != WEBSOCKET_STATE_STOPPING:
            self.state = WEBSOCKET_STATE_CONNECTING
            try:
                headers = None
                if self.api_key:
                    headers = [("X-Api-Key", self.api_key)]
                async with session.ws_connect(
                    self._build_websocket_uri(),
                    headers=headers,
                ) as ws:
                    if self.state == WEBSOCKET_STATE_STOPPING:
                        break

                    self._ws = ws
                    self.state = WEBSOCKET_STATE_CONNECTED
                    conn_event.set_result(True)

                    # This request should probably be moved into
                    # printer administration and respond to a connected
                    # event to remove knowledge of API specifics from this class
                    _, data = self._build_websocket_request("printer.objects.list")
                    await ws.send_json(data)

                    # Start the send/recv routines
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
                if error.code == 401:
                    _LOGGER.error("API access is unauthorized")
                    self.state = WEBSOCKET_STATE_STOPPING
                    conn_event.set_exception(ClientNotAuthenticatedError)
                    raise ClientNotAuthenticatedError
            except ClientConnectionError as error:
                _LOGGER.error("Websocket connection error: %s", error)
            except asyncio.TimeoutError:
                _LOGGER.error("Websocket connection timed out")
            except Exception as error:  # pylint: disable=broad-except
                _LOGGER.error("Websocket unknown error: %s", error)
                traceback.print_exc()
            finally:
                # Clean up pending requests
                for _ in range(self._requests_pending.qsize()):
                    self._requests_pending.get_nowait()
                    self._requests_pending.task_done()
                for req in self._requests.values():
                    req.cancel()

                # Stop was requested, do not try to reconnect
                if not self.retry or self.state == WEBSOCKET_STATE_STOPPING:
                    self.state = WEBSOCKET_STATE_STOPPED
                else:
                    self.state = WEBSOCKET_STATE_DISCONNECTED
                    await asyncio.sleep(WEBSOCKET_RETRY_DELAY)

    async def connect(self, blocking: bool = True) -> bool:
        """Start the run loop and connect

        Args:
            blocking (bool, optional): Default to `True`, waits for the
            connection to complete or timeout before returning.

        Note:
            Even if the connection fails, the update loop will keep trying
            to reconnect to websocket following a regular timeout. To stop
            this reconnect, call ``disconnect()``

        Returns:
            A ``boolean`` indicating if the connection succeeded, if
            ``blocking`` is False this will return False.
        """
        if self._runtask:
            raise ClientAlreadyConnectedError()

        conn_event = self._loop.create_future()
        self._runtask = self._loop.create_task(self._run(conn_event))
        if blocking:
            await asyncio.wait_for(conn_event, self._timeout)

        return self.is_connected

    async def disconnect(self):
        """Stop the websocket connection."""
        self._runtask = None

        if self.state != WEBSOCKET_STATE_STOPPED:
            self.state = WEBSOCKET_STATE_STOPPING

            if self._ws:
                await self._ws.close()
