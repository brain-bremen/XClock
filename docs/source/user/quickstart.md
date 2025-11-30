# Quick Start Guide

This guide will help you get started with XClock quickly. We'll cover basic usage patterns for both the Python library and command-line interface.

## Prerequisites

Make sure you have:

- Installed XClock (see {doc}`installation`)
- Installed your DAQ device drivers (e.g., LabJack LJM software)
- Connected your DAQ device via USB

## Your First Clock

Let's create a simple clock that runs for 5 seconds at 100 Hz.

### Using Python

```python
from xclock.devices import LabJackT4

# Initialize device
t4 = LabJackT4()

# Get available output channels
channels = t4.get_available_output_clock_channels()
print(f"Available channels: {channels}")

# Add a 100 Hz clock for 5 seconds
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=channels[0],
    duration_s=5.0,
)

# Start the clock and wait for completion
t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)

print("Clock finished!")
t4.close()
```

### Using CLI

```bash
xclock --clock-tick-rates 100 --duration 5 start
```

## Multiple Synchronized Clocks

One of XClock's key features is running multiple clocks simultaneously, all synchronized to the same base clock.

### Python Example

```python
from xclock.devices import LabJackT4

t4 = LabJackT4()
channels = t4.get_available_output_clock_channels()

# Add multiple clocks with different frequencies
t4.add_clock_channel(
    clock_tick_rate_hz=60,    # Camera 1 at 60 Hz
    channel_name=channels[0],
    duration_s=10.0,
)

t4.add_clock_channel(
    clock_tick_rate_hz=100,   # Camera 2 at 100 Hz
    channel_name=channels[1],
    duration_s=10.0,
)

# Start all clocks simultaneously
t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)
t4.close()
```

### CLI Example

```bash
xclock --clock-tick-rates 60,100 --duration 10 start
```

## Recording Timestamps

XClock can record precise timestamps of all clock edges, which is useful for synchronizing data post-acquisition.

### Python Example

```python
from xclock.devices import LabJackT4
import pathlib
import numpy as np

t4 = LabJackT4()
channels = t4.get_available_output_clock_channels()

# Add clocks
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=channels[0],
    duration_s=10.0,
)

# Start and record timestamps
output_file = pathlib.Path.home() / "Documents" / "XClock" / "timestamps.csv"
t4.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    filename=output_file
)

print(f"Timestamps saved to: {output_file}")

# Load and inspect the data
data = np.loadtxt(output_file, dtype=np.int64, delimiter=",")
print(f"Recorded {len(data)} edges")
print(f"First few timestamps:\n{data[:5]}")

t4.close()
```

### CLI Example

```bash
xclock --clock-tick-rates 100 --duration 10 --record-timestamps start
```

Timestamps are saved to `~/Documents/XClock/xclock_timestamps_<timestamp>.csv`

## Understanding the Timestamp Format

The CSV file contains three columns:

1. **Timestamp (nanoseconds)**: Time since device start (relative timing)
2. **Edge type**: Indicates which clock and edge direction
   - Positive number (e.g., `1`, `2`): Rising edge on clock 1, 2, etc.
   - Negative number (e.g., `-1`, `-2`): Falling edge on clock 1, 2, etc.
3. **Unix timestamp (nanoseconds)**: Host system time (absolute timing)

Example:

```
1000000,1,1638360000000000000      # Rising edge on clock 1 at 1ms (device time)
1500000,-1,1638360000500000000     # Falling edge on clock 1 at 1.5ms
2000000,1,1638360001000000000      # Rising edge on clock 1 at 2ms
2000000,2,1638360001000000000      # Rising edge on clock 2 at 2ms (same device time)
```

The Unix timestamp (column 3) allows you to correlate events with other systems or absolute wall-clock time.

## Continuous vs. Pulsed Clocks

XClock supports two modes:

### Continuous Clocks

Runs indefinitely until manually stopped.

```python
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=channels[0],
    number_of_pulses=None,  # None = continuous
)

t4.start_clocks(wait_for_pulsed_clocks_to_finish=False)

# Do your experiment...
import time
time.sleep(30)

# Stop when done
t4.stop_clocks()
```

### Pulsed Clocks

Generates a specific number of pulses then stops automatically.

```python
# Specify exact pulse count
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=channels[0],
    number_of_pulses=1000,  # Exactly 1000 pulses
)

# Or use duration (auto-calculates pulses)
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=channels[0],
    duration_s=10.0,  # 100 Hz * 10s = 1000 pulses
)
```

## Trigger-Based Start

Start clocks when an external trigger signal is received.

### Python Example

```python
from xclock.devices import LabJackT4, EdgeType

t4 = LabJackT4()
channels = t4.get_available_output_clock_channels()
trigger_channels = t4.get_available_input_start_trigger_channels()

# Add clocks (but don't start yet)
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=channels[0],
    duration_s=10.0,
)

print(f"Waiting for trigger on {trigger_channels[0]}...")
print("Send a rising edge to start the clock.")

# Wait for trigger
triggered = t4.wait_for_trigger_edge(
    channel_name=trigger_channels[0],
    timeout_s=30.0,
    edge_type=EdgeType.RISING,
)

if triggered:
    print("Trigger received! Starting clocks...")
    t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)
else:
    print("Timeout waiting for trigger")

t4.close()
```

### CLI Example

```bash
xclock --clock-tick-rates 100 --duration 10 --when on_trigger --timeout 30 start
```

## Common Patterns

### Pattern 1: Synchronize Two Cameras

```python
from xclock.devices import LabJackT4

t4 = LabJackT4()
channels = t4.get_available_output_clock_channels()

# Behavior camera at 60 Hz
t4.add_clock_channel(60, channels[0], duration_s=300)  # 5 minutes

# Imaging camera at 30 Hz
t4.add_clock_channel(30, channels[1], duration_s=300)

# Record all frame timestamps
t4.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    filename="camera_sync.csv"
)
```

### Pattern 2: Test Device Connectivity

```python
from xclock.devices import LabJackT4

try:
    t4 = LabJackT4()
    print(f"✓ Connected to LabJack T4")
    print(f"✓ Base clock: {t4.base_clock_frequency_hz} Hz")
    print(f"✓ Available channels: {t4.get_available_output_clock_channels()}")
    t4.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

### Pattern 3: Short Test Pulse

Useful for testing wiring and connections:

```python
from xclock.devices import LabJackT4

t4 = LabJackT4()
channels = t4.get_available_output_clock_channels()

# Generate 10 pulses at 10 Hz (1 second total)
t4.add_clock_channel(
    clock_tick_rate_hz=10,
    channel_name=channels[0],
    number_of_pulses=10,
)

t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)
print("Test pulses complete!")
t4.close()
```

## Next Steps

Now that you understand the basics:

- Learn about {doc}`cli` for more command-line options
- Read {doc}`devices` for device-specific features
- Explore the {doc}`../api/devices` for advanced usage

## Common Issues

### Clock frequency not exactly as requested

XClock calculates the closest achievable frequency based on the device's base clock and divisor limitations. The actual frequency is returned in the `ClockChannel.actual_sample_rate_hz` field.

```python
channel = t4.add_clock_channel(clock_tick_rate_hz=100, ...)
print(f"Requested: 100 Hz, Actual: {channel.actual_sample_rate_hz} Hz")
```

### Device already in use

If you get an error about the device being in use:

1. Make sure you called `close()` on previous device instances
2. Check if another process is using the device
3. Disconnect and reconnect the device
4. Restart your Python kernel/terminal

### No pulses generated

Common causes:

- Clock not started with `start_clocks()`
- `number_of_pulses` set to 0
- Device not properly connected
- Check the physical wiring and connections