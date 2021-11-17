import argparse
import asyncio
import logging

from moonraker_api import MoonrakerClient, MoonrakerListener


logging.basicConfig(
    level=logging.WARNING, format="%(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("moonraker_api").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)
_LOGGER = logging.getLogger(__name__)


class WSHandler(MoonrakerListener):
    """Handle incoming events from the Moonraker API client"""

    async def state_changed(self, state: str) -> None:
        """Called when the websocket state changes"""
        _LOGGER.debug("Handling state_changed event to %s", state)


async def main(args):
    """Bootstrap function"""
    if not args.host:
        _LOGGER.error("Need to specify a hostname")
        return

    listener = WSHandler()
    client = MoonrakerClient(host=args.host, listener=listener)
    await client.connect()

    if args.reset:
        await client.printer_administration.restart()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Moonraker API command line client.")
    parser.add_argument("--discovery", default=False, action="store_true")
    parser.add_argument("--host", default="atlas.local", metavar="h")
    parser.add_argument("--reset", default=False, action="store_true")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(parser.parse_args()))
