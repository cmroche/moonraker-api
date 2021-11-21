# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

CHANNEL_PRINTERADMINISTRATION = "channel_printeradministration"
CHANNEL_PRINTERUPDATES = "channel_printerupdates"
CHANNELS_ALL = [CHANNEL_PRINTERADMINISTRATION, CHANNEL_PRINTERUPDATES]

WEBSOCKET_STATE_CONNECTING = "ws_connecting"
WEBSOCKET_STATE_CONNECTED = "ws_connected"
WEBSOCKET_STATE_STOPPING = "ws_stopping"
WEBSOCKET_STATE_STOPPED = "ws_stopped"

WEBSOCKET_CONNECTION_TIMEOUT = 120  # seconds
WEBSOCKET_RETRY_DELAY = 30  # seconds
