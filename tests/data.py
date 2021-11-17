# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

TEST_DATA_UPDATE = {
    "jsonrpc": "2.0",
    "method": "notify_proc_stat_update",
    "params": [
        {
            "moonraker_stats": {
                "time": 1636922183.5641754,
                "cpu_usage": 5.58,
                "memory": 26548,
                "mem_units": "kB",
            },
            "cpu_temp": 48.312,
            "network": {
                "lo": {
                    "rx_bytes": 89432207,
                    "tx_bytes": 89432207,
                    "bandwidth": 4506.44,
                },
                "eth0": {
                    "rx_bytes": 73164330,
                    "tx_bytes": 100031803,
                    "bandwidth": 4426.43,
                },
                "wlan0": {"rx_bytes": 0, "tx_bytes": 0, "bandwidth": 0},
            },
            "websocket_connections": 2,
        }
    ],
}

TEST_DATA_PRINTER_INFO = {
    "state": "ready",
    "state_message": "Printer is ready",
    "hostname": "my-pi-hostname",
    "software_version": "v0.9.1-302-g900c7396",
    "cpu_info": "4 core ARMv7 Processor rev 4 (v7l)",
    "klipper_path": "/home/pi/klipper",
    "python_path": "/home/pi/klippy-env/bin/python",
    "log_file": "/tmp/klippy.log",
    "config_file": "/home/pi/printer.cfg",
}

TEST_DATA_SUPPORTED_MODULES = {
    "objects": ["gcode", "toolhead", "bed_mesh", "configfile"]
}

TEST_METHOD_RESPONSES = {
    "printer.info": TEST_DATA_PRINTER_INFO,
    "printer.objects.list": TEST_DATA_SUPPORTED_MODULES,
}
