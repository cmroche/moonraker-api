# Moonraker API Client
#
# Copyright (C) 2021 Clifford Roche <clifford.roche@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license

"""Test data responses."""

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
    "jsonrpc": "2.0",
    "result": {
        "state_message": "Printer is ready",
        "klipper_path": "/home/pi/klipper",
        "config_file": "/home/pi/klipper_config/printer.cfg",
        "software_version": "v0.10.0-129-g4861a0d9",
        "hostname": "atlas",
        "cpu_info": "4 core ARMv7 Processor rev 4 (v7l)",
        "state": "ready",
        "python_path": "/home/pi/klippy-env/bin/python",
        "log_file": "/home/pi/klipper_logs/klippy.log",
    },
    "id": 1,
}

TEST_DATA_SUPPORTED_MODULES = {
    "jsonrpc": "2.0",
    "result": {
        "objects": [
            "webhooks",
            "configfile",
            "mcu",
            "idle_timeout",
            "gcode_move",
            "menu",
            "display_status",
            "tmc2209 extruder",
            "heaters",
            "heater_fan hotend_fan",
            "fan",
            "print_stats",
            "virtual_sdcard",
            "pause_resume",
            "gcode_macro PAUSE",
            "gcode_macro RESUME",
            "gcode_macro CANCEL_PRINT",
            "heater_bed",
            "gcode_macro PRINT_START",
            "gcode_macro PRINT_END",
            "gcode_macro LOAD_FILAMENT",
            "gcode_macro UNLOAD_FILAMENT",
            "tmc2209 stepper_x",
            "tmc2209 stepper_y",
            "tmc2209 stepper_z",
            "motion_report",
            "query_endstops",
            "system_stats",
            "toolhead",
            "extruder",
        ]
    },
    "id": 0,
}

TEST_DATA_OBJECTS_QUERY = {
    "jsonrpc": "2.0",
    "result": {
        "eventtime": 578243.57824499,
        "status": {
            "gcode_move": {
                "absolute_coordinates": True,
                "absolute_extrude": True,
                "extrude_factor": 1,
                "gcode_position": [0, 0, 0, 0],
                "homing_origin": [0, 0, 0, 0],
                "position": [0, 0, 0, 0],
                "speed": 1500,
                "speed_factor": 1,
            },
            "toolhead": {"position": [0, 0, 0, 0], "status": "Ready"},
        },
    },
    "id": 0,
}

TEST_DATA_SERVER_INFO_RESPONSE = {
    "jsonrpc": "2.0",
    "result": {
        "klippy_connected": True,
        "klippy_state": "ready",
        "components": [
            "database",
            "file_manager",
            "klippy_apis",
            "machine",
            "data_store",
            "shell_command",
            "proc_stats",
            "history",
            "octoprint_compat",
            "update_manager",
            "power",
        ],
        "failed_components": [],
        "registered_directories": ["config", "gcodes", "config_examples", "docs"],
        "warnings": [
            "Invalid config option 'api_key_path' detected in section [authorization]. Remove the option to resolve this issue. In the future this will result in a startup error.",
            "Unparsed config section [fake_section] detected.  This may be the result of a component that failed to load.  In the future this will result in a startup error.",
        ],
        "websocket_count": 2,
        "moonraker_version": "v0.7.1-105-ge4f103c",
    },
    "id": 0,
}

TEST_DATA_SIMPLE_NOTIFICATION = {
    "jsonrpc": "2.0",
    "method": "notify_gcode_response",
    "params": ["response message"],
}

TEST_DATA_SIMPLE_RESPONSE = {
    "jsonrpc": "2.0",
    "result": {"res_data": "success"},
    "id": 0,
}

TEST_METHOD_RESPONSES = {
    # Simple test responses first
    "printer.restart": TEST_DATA_SIMPLE_RESPONSE,
    "printer.emergency_stop": TEST_DATA_SIMPLE_RESPONSE,
    "printer.firmware_restart": TEST_DATA_SIMPLE_RESPONSE,
    # Complex test responses (have their own data)
    "printer.info": TEST_DATA_PRINTER_INFO,
    "printer.objects.list": TEST_DATA_SUPPORTED_MODULES,
    "printer.objects.query": TEST_DATA_OBJECTS_QUERY,
    "server.info": TEST_DATA_SERVER_INFO_RESPONSE,
    # Special cases to assist testing
    "testing.send_gcode_response": TEST_DATA_SIMPLE_RESPONSE,
}
