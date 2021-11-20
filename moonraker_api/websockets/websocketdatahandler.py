# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

import logging
from typing import TypedDict

_LOGGER = logging.getLogger(__name__)


class WebsocketDataHandler:
    """Base class for registering and handling incoming
    websocket data
    """

    async def process_data_message(self, _: TypedDict) -> bool:
        """Process incoming data message.

        Returns: True if message consumed, False othewise
        """
        return False
