![Python package](https://github.com/cmroche/moonraker-api/workflows/Python%20package/badge.svg)

## Moonracker Websocket API Client

Connect, request and subscribe to the Moonraker Websockets API without polling.

**moonraker-api** is a ***fully async*** Python 3 based package for interfacing with Moonraker's API.

## Getting the package

The easiest way to grab **moonraker-api** is through PyPI
`pip3 install moonraker-api`

## Use Moonraker-API

### Connect and Disconnect

```python
class APIConnector(MoonrakerListener):
    def __init__():
        self.running = False
        self.client = MoonrakerClient(
            self,
            HOST,
            PORT,
            API-KEY,
        )

    async def start(self) -> None:
        """Start the websocket connection."""
        self.running = True
        return await self.client.connect()

    async def stop(self) -> None:
        """Stop the websocket connection."""
        self.running = False
        await self.client.disconnect()
```

### Query the API

```python
api_connector = APIConnector()
response = await api_connector.client.request("printer.info")
```

### Handle Push Notifications

```python
class APIConnector(MoonrakerListener):

    # Other class details, see above ...

    async def state_changed(self, state: str) -> None:
        """Notifies of changing websocket state."""
        _LOGGER.debug("Stated changed to %s", state)
        if state == WEBSOCKET_STATE_CONNECTING:
            pass
        elif state == WEBSOCKET_STATE_CONNECTED:
            pass
        elif state == WEBSOCKET_STATE_READY:
            pass
        elif state == WEBSOCKET_STATE_PASSED:
            pass
        elif state == WEBSOCKET_STATE_STOPPED:
            pass

    async def on_exception(self, exception: BaseException) -> None:
        """Notifies of exceptions from the websocket run loop."""
        _LOGGER.debug("Received exception from API websocket %s", str(exception))
        if isinstance(exception, ClientNotAuthenticatedError):
            self.entry.async_start_reauth(self.hass)
        else:
            raise exception

    async def on_notification(self, method: str, data: Any) -> None:
        """Notifies of state updates."""
        _LOGGER.debug("Received notification %s -> %s", method, data)

        # Subscription notifications
        if method == "notify_status_update":
            message = data[0]
            timestamp = data[1]
            
            # Do stuff ...
```
