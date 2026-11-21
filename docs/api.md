# Moonraker API reference

Use this reference to connect to Moonraker, make JSON-RPC requests, and
receive notifications with `MoonrakerClient`. All methods marked `async` must
be awaited from an asyncio event loop.

## Connect to Moonraker

Create the client inside a running event loop, connect, and disconnect when
finished. Replace `MOONRAKER_HOST` with your printer's hostname or IP address:

```python
import asyncio

from moonraker_api import MoonrakerClient, MoonrakerListener


async def main():
    client = MoonrakerClient(listener=MoonrakerListener(), host="MOONRAKER_HOST")
    try:
        await client.connect()
        print(await client.get_server_info())
    finally:
        await client.disconnect()


asyncio.run(main())
```

### `MoonrakerClient(...)`

| Parameter | Default | Meaning |
| --- | --- | --- |
| `listener` | Required | `MoonrakerListener` receiving connection events and notifications; pass `None` to ignore them. |
| `host` | Required | Moonraker hostname or IP address. |
| `port` | `7125` | Websocket server port. |
| `route_prefix` | `None` | Optional path prefix before `/websocket`; surrounding slashes are removed. |
| `api_key` | `None` | Optional API key sent in the `X-Api-Key` header. |
| `ssl` | `False` | Use `wss://` rather than `ws://` when true. |
| `loop` | `None` | Event loop for client tasks; defaults to the current event loop. |
| `timeout` | `120` | Connection, websocket receive, and request timeout in seconds. |
| `session` | `None` | Optional `aiohttp.ClientSession`. The caller retains ownership. |

The client closes a session it creates during disconnect or connection failure;
it does not close a caller-supplied session.

### `MoonrakerClient.connect()`

Signature: `async def connect() -> bool`

Opens the websocket and returns its connection state. Raises
`ClientAlreadyConnectedError` if a connection task is already active;
authentication, connection, and timeout errors propagate. Connecting does
not imply Klipper is ready.

If `connect()` times out, its background handshake may still be running.
Await `disconnect()` before retrying; it may wait for that handshake to finish.
See [Connect to Moonraker](#connect-to-moonraker) for an example.

### `MoonrakerClient.disconnect()`

Signature: `async def disconnect() -> None`

Closes the websocket and waits for its run task to finish. See
[Connect to Moonraker](#connect-to-moonraker) for an example.

### Connection properties

- `client.is_connected` is true only in the `ws_connected` state.
- `client.state` is the current websocket state. `client.tasks` contains
  outstanding client-managed callback tasks.

Connection states can be imported from `moonraker_api.const`:

| Constant | Value |
| --- | --- |
| `WEBSOCKET_STATE_CONNECTING` | `ws_connecting` |
| `WEBSOCKET_STATE_CONNECTED` | `ws_connected` |
| `WEBSOCKET_STATE_STOPPING` | `ws_stopping` |
| `WEBSOCKET_STATE_STOPPED` | `ws_stopped` |

## Requests

### `MoonrakerClient.call_method()`

Signature: `async def call_method(method: str, **kwargs: Any) -> Any`

Calls a Moonraker JSON-RPC method and returns its `result`. Keyword arguments
become the request's `params` object. When Moonraker returns a JSON-RPC error,
the result is `{"error": ...}` rather than an exception. A disconnected client
raises `ClientNotConnectedError`; connection failures and timeouts can also
propagate. If the websocket closes while a request is pending, the request may
raise `asyncio.CancelledError`.

With a connected `client` in an async function and Klipper ready, query the
extruder's temperature and target:

```python
reply = await client.call_method(
    "printer.objects.query",
    objects={"extruder": ["temperature", "target"]},
)
if "error" in reply:
    print("Query failed:", reply["error"])
else:
    print(reply["status"])
```

`reply["status"]` contains the fields returned by Moonraker; missing objects
or fields may be omitted. See the
[Moonraker printer object API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
for methods and request fields.

### `MoonrakerClient.request()`

Signature: `def request(method: str, **kwargs: Any) -> AwaitableTaskContext`

Returns an async context manager for a lower-level request. Enter the context
to queue it, then await `get_result()` on the yielded request. The request is
removed from the client's pending-response registry when the context exits.
Like `call_method`, it requires an active connection.

With a connected `client` in an async function, request printer information:

```python
async with client.request("printer.info") as request:
    info = await request.get_result()
print(info)
```

The yielded request also exposes `req_id`, `timeout`, and `done` properties,
`wait()`, and `cancel()`. Cancellation only cancels the local result future:
it does not withdraw a queued request or prevent Moonraker from executing it.
A reply arriving while the cancelled request is still registered can cause an
`InvalidStateError` and close the websocket. Prefer `call_method` unless direct
access to the request is needed.

## Client convenience methods

Run these examples inside an async function with a connected `client`. These
methods share the connection, timeout, and cancellation behavior described in
[`call_method`](#moonrakerclientcall_method).

### `MoonrakerClient.get_host_info()`

Signature: `async def get_host_info() -> Any`

Returns the `printer.info` result, containing Klipper host information such as
its current state and hostname. An RPC error is returned as an `error` mapping.

```python
info = await client.get_host_info()
if "error" in info:
    print("Printer info unavailable:", info["error"])
else:
    print("Klipper state:", info["state"])
    print("Printer hostname:", info["hostname"])
```

### `MoonrakerClient.get_server_info()`

Signature: `async def get_server_info() -> Any`

Returns the `server.info` result, containing Moonraker server information and
Klipper's connection state. An RPC error is returned as an `error` mapping.

```python
info = await client.get_server_info()
if "error" in info:
    print("Server info unavailable:", info["error"])
else:
    print("Klipper state:", info["klippy_state"])
    print("Moonraker version:", info["moonraker_version"])
```

### `MoonrakerClient.get_supported_modules()`

Signature: `async def get_supported_modules() -> list[str] | None`

Returns the `objects` list from `printer.objects.list`, containing full
Klipper object names. Returns `None` when the reply has no `objects` field,
including an RPC error. Query after Klipper is ready.

```python
objects = await client.get_supported_modules()
if objects is None:
    print("Printer object list unavailable")
else:
    for name in objects:
        print(name)  # For example, "extruder" or "temperature_sensor chamber"
```

### `MoonrakerClient.get_klipper_status()`

Signature: `async def get_klipper_status() -> Literal["ready", "shutdown", "disconnected"]`

Returns `klippy_state` from `server.info`. Moonraker may return `disconnected`,
`startup`, `ready`, `error`, or `shutdown`; the current Python type annotation
omits `startup` and `error`. Raises `KeyError` if `klippy_state` is absent,
including when the RPC returns an error mapping.

```python
try:
    state = await client.get_klipper_status()
except KeyError:
    print("Klipper state unavailable")
else:
    print("Klipper state:", state)
    if state == "ready":
        print("Klipper is ready for printer object requests")
```

### `MoonrakerClient.get_websocket_id()`

Signature: `async def get_websocket_id() -> Any`

Returns the `server.websocket.id` result, a mapping containing the integer
`websocket_id`, or an RPC error mapping. Moonraker deprecates this endpoint in
favor of [`server.connection.identify`](https://moonraker.readthedocs.io/en/latest/external_api/server/#identify-connection),
whose result includes `connection_id`.

```python
result = await client.get_websocket_id()
if "error" in result:
    print("Websocket ID unavailable:", result["error"])
else:
    print("Websocket ID:", result["websocket_id"])
```

### `MoonrakerClient.get_temperature_sensors()`

Signature: `async def get_temperature_sensors() -> list[str] | None`

Returns full names of registered thermal objects, including heaters, chamber
probes, and temperature monitors. Call after Klipper is ready. Sensors come
first, then monitors, in the order reported by Klipper; duplicates are removed.
Returns `[]` when no sources are registered, or `None` when the reply has no
`status` result. Discovery does not read temperatures or change subscriptions.

With a connected `client` and Klipper ready, query the current temperatures:

```python
names = await client.get_temperature_sensors()

if names is None:
    print("Temperature discovery failed")
elif not names:
    print("No thermal sources registered")
else:
    # For example: ["extruder", "heater_bed", "temperature_sensor chamber_top"]
    reply = await client.call_method(
        "printer.objects.query",
        objects={name: ["temperature"] for name in names},
    )
    if "status" not in reply:
        print("Temperature query failed")
    else:
        for name, fields in reply["status"].items():
            if "temperature" in fields:
                value = fields["temperature"]
                reading = "unavailable" if value is None else f"{value} °C"
                print(f"{name}: {reading}")
```

For live readings, merge the fields into the existing subscription; see
[Notifications](#notifications).

## Notifications

Subclass `MoonrakerListener` and override its async callbacks:

- `state_changed(state)` receives websocket state changes.
- `on_exception(exception)` receives an exception from the websocket run loop.
  For an HTTP 401, the argument can be the `ClientNotAuthenticatedError` class
  rather than an instance. Do not await `disconnect()` inside this callback:
  the run loop waits for it, causing a circular wait. Signal an outer task to
  disconnect after the callback returns.
- `on_notification(method, data)` receives the notification method and its
  JSON-RPC `params`, or `None` if `params` is absent. Callbacks are scheduled
  as tasks; avoid relying on their completion order.

Define a listener for status updates:

```python
class Listener(MoonrakerListener):
    async def on_notification(self, method, data):
        if method == "notify_status_update":
            changed_objects, eventtime = data
            print(eventtime, changed_objects)
```

Construct and connect the client using [Connect to Moonraker](#connect-to-moonraker),
passing `Listener()` instead of `MoonrakerListener()`. After Klipper is ready,
run this subscription inside an async function:

```python
reply = await client.call_method(
    "printer.objects.subscribe",
    objects={"print_stats": None, "extruder": ["temperature"]},
)
if "status" in reply:
    print("Initial status:", reply["status"])
else:
    print("Subscription failed:", reply)
```

Subscribe with the complete set of objects needed on the connection: each
subscription replaces the previous one, and an empty selection cancels it.
The reply contains initial status; later `notify_status_update` messages
contain changed fields, not complete snapshots. An omitted field leaves the
previous value unchanged. After reconnecting or restarting Klipper, wait until
Klipper is ready and rebuild subscriptions. See [Moonraker notifications](https://moonraker.readthedocs.io/en/latest/external_api/jsonrpc_notifications/)
for notification payloads.

## Exceptions

These exceptions are importable from `moonraker_api`:

- `ClientAlreadyConnectedError`: `connect()` was called while its run task is
  active.
- `ClientNotConnectedError`: a request was made while the websocket was not
  connected.
- `ClientNotAuthenticatedError`: the websocket handshake received HTTP 401.

Other connection and timeout exceptions may propagate. An RPC-level error is
returned as a mapping, not raised as one of these exceptions.

