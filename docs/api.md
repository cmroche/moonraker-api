# Moonraker API reference

Use this reference to discover and read Klipper temperatures with a connected [`MoonrakerClient`](../README.md#connect-and-disconnect).

## `MoonrakerClient.get_temperature_sensors()`

```python
async def get_temperature_sensors(self) -> list[str] | None
```

Returns the full names of registered thermal objects, including heaters, chamber probes, and temperature monitors. Call this method after Klipper is ready. Sensors come first, then monitors, in the order reported by Klipper. If a name appears more than once, only its first occurrence is kept.

Returns `[]` when the query succeeds but no sources are registered, or `None` when Moonraker's reply has no `status` result. Connection errors and timeouts propagate. Discovery does not read temperatures or change subscriptions.

### Read the current temperatures

With a connected `client`, use the names as keys in a single query for the `temperature` field. Run this snippet inside an async function:

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

For live readings instead, merge these fields into the connection's existing `printer.objects.subscribe` request. Each subscription replaces the previous one on that connection; it doesn't add to it.
