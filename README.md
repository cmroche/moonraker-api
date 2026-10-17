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
        elif state == WEBSOCKET_STATE_PAUSED:
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

## Releases and PyPI publishing

Pushes to `main` run the Python test matrix, then semantic-release updates the
package version and changelog and creates the release tag and GitHub release.
It does not upload to PyPI or use PyPI credentials.

The release job dispatches `.github/workflows/pypi.yml` at the new tag because
tags created with `GITHUB_TOKEN` do not trigger tag-push workflows. The publishing
workflow also accepts `v*` tag pushes and manual dispatches **at a tag**, not a
branch. Its gate requires a stable `vMAJOR.MINOR.PATCH` tag matching the version
in `setup.cfg`, with the checked-out commit reachable from `main`.

Distributions are built and checked without publishing credentials, then passed
as workflow artifacts to a separate upload job. Only that job has
`id-token: write`; it uses PyPI Trusted Publishing and uploads PEP 740
attestations with the wheel and source distribution.

### One-time maintainer setup

Complete this setup before enabling the new publishing workflow:

1. In this repository's GitHub settings, create an environment named `pypi`.
   Set its deployment policy to **Selected branches and tags**, allowing only
   **tags** matching `v*`, with no branch deployment rules.
2. Add an active tag ruleset targeting `refs/tags/v*` that restricts updates and
   deletions, with no bypass actors. Allow new tag creation so semantic-release
   can create releases.
3. In [the PyPI project's publishing settings](https://pypi.org/manage/project/moonraker-api/settings/publishing/),
   register this GitHub Trusted Publisher:

   | Field | Value |
   | --- | --- |
   | Owner | `cmroche` |
   | Repository | `moonraker-api` |
   | Workflow filename | `pypi.yml` |
   | Environment | `pypi` |

4. After the first successful OIDC upload, verify the release's attestations on
   PyPI, then remove the GitHub `PYPI_TOKEN` and `PYPI_USER` secrets and revoke the
   old PyPI token. There is no static-token fallback.

To recover a failed handoff, dispatch the existing release tag:
`gh workflow run pypi.yml --ref vX.Y.Z`. Branch dispatches cannot publish.
Already-published versions are not silently skipped; PyPI versions and release
tags must not be overwritten. Attestations apply to new uploads, not historical
files already on PyPI.

See [PyPI's Trusted Publisher setup](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
and [PyPA's publishing action](https://github.com/pypa/gh-action-pypi-publish)
for the authentication and attestation requirements.
