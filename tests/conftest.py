# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license
import pytest

from unittest.mock import Mock

from moonraker_api.moonrakerclient import MoonrakerClient, MoonrakerListener


# class FakeWSHandler(MoonrakerListener):
#     """Handle incomgin events from the Moonraker API client"""

#     def __init__(self):
#         """Initialize the listener"""
#         super().__init__()

#     async def state_changed(self, state: str) -> None:
#         """Called when the websocket state changes"""


@pytest.fixture(name="moonraker")
def moonraker_client():
    """Create a simple api client for testing"""
    h = Mock(name="MoonrakeListener", spec=MoonrakerListener)
    c = MoonrakerClient(host="127.0.0.1", port=7125, listener=h)
    return c
