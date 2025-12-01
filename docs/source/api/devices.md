# Devices API Reference

This page provides detailed API documentation for XClock device classes and related types.

## Overview

The devices module provides the core abstractions and implementations for controlling DAQ devices as clock generators.

```python
from xclock.devices import ClockDaqDevice, LabJackT4, DummyDaqDevice
from xclock.devices import ClockChannel, EdgeType
```

## Abstract Base Class

### `ClockDaqDevice`

Abstract base class that all device implementations must inherit from.

```python
class ClockDaqDevice(ABC):
    """
    Abstract base class for all clock DAQ devices.
    
    Attributes:
        handle: Device handle or connection identifier
        base_clock_frequency_hz: Base clock frequency of the device
    """
```

#### Class Methods

##### `get_available_output_clock_channels()`

```python
@staticmethod
@abstractmethod
def get_available_output_clock_channels() -> tuple[str, ...]
```

Returns a tuple of channel names that can be used for clock output.

**Returns:**
- `tuple[str, ...]`: Channel names (e.g., `("FIO0", "FIO1", "FIO2")`)

**Example:**
```python
channels = LabJackT4.get_available_output_clock_channels()
print(channels)  # ("FIO0", "FIO1", ..., "EIO3")
```

##### `get_available_input_start_trigger_channels()`

```python
@staticmethod
@abstractmethod
def get_available_input_start_trigger_channels() -> tuple[str, ...]
```

Returns a tuple of channel names that can be used as trigger inputs.

**Returns:**
- `tuple[str, ...]`: Trigger channel names (e.g., `("DIO4",)`)

**Example:**
```python
triggers = LabJackT4.get_available_input_start_trigger_channels()
print(triggers)  # ("DIO4",)
```

#### Instance Methods

##### `__init__()`

```python
def __init__(self)
```

Initialize the device and establish connection.

**Raises:**
- `XClockException`: If device initialization fails

**Example:**
```python
try:
    device = LabJackT4()
except XClockException as e:
    print(f"Failed to initialize: {e}")
```

##### `get_added_clock_channels()`

```python
@abstractmethod
def get_added_clock_channels(self) -> list[ClockChannel]
```

Returns a list of currently configured clock channels.

**Returns:**
- `list[ClockChannel]`: List of configured clocks

**Example:**
```python
device = LabJackT4()
device.add_clock_channel(100, "FIO0")
device.add_clock_channel(60, "FIO1")
clocks = device.get_added_clock_channels()
print(len(clocks))  # 2
```

##### `get_unused_clock_channel_names()`

```python
@abstractmethod
def get_unused_clock_channel_names(self) -> list[str]
```

Returns a list of channel names that are available (not yet configured).

**Returns:**
- `list[str]`: Unused channel names

**Example:**
```python
device = LabJackT4()
device.add_clock_channel(100, "FIO0")
unused = device.get_unused_clock_channel_names()
print("FIO0" in unused)  # False
print("FIO1" in unused)  # True
```

##### `add_clock_channel()`

```python
@abstractmethod
def add_clock_channel(
    self,
    clock_tick_rate_hz: int | float,
    channel_name: str | None = None,
    number_of_pulses: int | None = None,
    duration_s: float | None = None,
    enable_clock_now: bool = False,
) -> ClockChannel
```

Configure a new clock channel.

**Parameters:**
- `clock_tick_rate_hz` (int | float): Desired clock frequency in Hz
- `channel_name` (str | None): Output channel name, or None for auto-select
- `number_of_pulses` (int | None): Number of pulses to generate, or None for continuous
- `duration_s` (float | None): Duration in seconds (auto-calculates pulses)
- `enable_clock_now` (bool): If True, start this clock immediately

**Returns:**
- `ClockChannel`: Configured clock channel object

**Raises:**
- `XClockException`: If channel is invalid or already in use
- `XClockValueError`: If parameters are invalid

**Notes:**
- `duration_s` and `number_of_pulses` are mutually exclusive
- If both are None, clock runs continuously
- Actual frequency may differ from requested (see `ClockChannel.actual_sample_rate_hz`)

**Example:**
```python
device = LabJackT4()

# Continuous clock
clock1 = device.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name="FIO0",
)

# Pulsed clock with exact count
clock2 = device.add_clock_channel(
    clock_tick_rate_hz=60,
    channel_name="FIO1",
    number_of_pulses=1000,
)

# Pulsed clock with duration
clock3 = device.add_clock_channel(
    clock_tick_rate_hz=30,
    duration_s=10.0,  # 30 Hz * 10s = 300 pulses
)
```

##### `start_clocks()`

```python
@abstractmethod
def start_clocks(
    self,
    wait_for_pulsed_clocks_to_finish: bool = False,
)
```

Start all configured clocks simultaneously.

**Parameters:**
- `wait_for_pulsed_clocks_to_finish` (bool): If True, block until pulsed clocks complete

**Raises:**
- `XClockException`: If no clocks configured or start fails

**Example:**
```python
device = LabJackT4()
device.add_clock_channel(100, "FIO0", number_of_pulses=500)

# Start and wait for completion
device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
print("All pulses generated!")

# Or start without waiting
device.start_clocks(wait_for_pulsed_clocks_to_finish=False)
# Do other work...
device.stop_clocks()
```

##### `stop_clocks()`

```python
@abstractmethod
def stop_clocks(self)
```

Stop all running clocks immediately.

**Example:**
```python
device = LabJackT4()
device.add_clock_channel(100, "FIO0")
device.start_clocks()

import time
time.sleep(5)  # Run for 5 seconds

device.stop_clocks()
```

##### `clear_clocks()`

```python
@abstractmethod
def clear_clocks(self)
```

Remove all configured clocks and stop them if running.

**Example:**
```python
device = LabJackT4()
device.add_clock_channel(100, "FIO0")
device.add_clock_channel(60, "FIO1")

device.clear_clocks()
print(len(device.get_added_clock_channels()))  # 0
```

##### `wait_for_trigger_edge()`

```python
@abstractmethod
def wait_for_trigger_edge(
    self,
    channel_name: str,
    timeout_s: float = 5.0,
    edge_type: EdgeType = EdgeType.RISING,
) -> bool
```

Wait for an edge on the specified trigger input channel.

**Parameters:**
- `channel_name` (str): Trigger input channel name
- `timeout_s` (float): Timeout in seconds (0 or negative = infinite)
- `edge_type` (EdgeType): Type of edge to wait for

**Returns:**
- `bool`: True if triggered, False if timeout

**Raises:**
- `XClockException`: If channel is invalid

**Example:**
```python
device = LabJackT4()
device.add_clock_channel(100, "FIO0", duration_s=10)

print("Waiting for trigger...")
triggered = device.wait_for_trigger_edge(
    channel_name="DIO4",
    timeout_s=30.0,
    edge_type=EdgeType.RISING,
)

if triggered:
    print("Trigger received! Starting clocks...")
    device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
else:
    print("Timeout - no trigger received")
```

##### `start_clocks_and_record_edge_timestamps()`

```python
@abstractmethod
def start_clocks_and_record_edge_timestamps(
    self,
    wait_for_pulsed_clocks_to_finish: bool = True,
    extra_channels: list[str] = [],
    filename: Path | str | None = None,
)
```

Start clocks and record edge timestamps to a CSV file.

**Parameters:**
- `wait_for_pulsed_clocks_to_finish` (bool): Block until pulsed clocks finish
- `extra_channels` (list[str]): Additional channels to monitor for edges
- `filename` (Path | str | None): Output file path, or None for auto-generate

**Output Format:**
CSV file with three columns:
- Column 1: Timestamp in nanoseconds (int64) - Device-relative time since start
- Column 2: Edge type (int8)
  - Positive: Rising edge on clock N
  - Negative: Falling edge on clock N
- Column 3: Unix timestamp in nanoseconds (int64) - Host system time

**Example:**
```python
from pathlib import Path

device = LabJackT4()
device.add_clock_channel(100, "FIO0", duration_s=10)
device.add_clock_channel(60, "FIO1", duration_s=10)

output = Path.home() / "Documents" / "XClock" / "sync.csv"
device.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    extra_channels=["EIO4"],  # Also monitor EIO4
    filename=output,
)

# Load and analyze
import numpy as np
data = np.loadtxt(output, dtype=np.int64, delimiter=",")
timestamps_ns = data[:, 0]      # Device-relative timestamps
edge_types = data[:, 1]          # Edge type
unix_timestamps_ns = data[:, 2]  # Unix timestamps (host time)
print(f"Recorded {len(data)} edges")
```

##### `close()`

```python
@abstractmethod
def close(self)
```

Clean up resources and close device connection.

Always call this when done, or use context manager if supported.

**Example:**
```python
device = LabJackT4()
try:
    device.add_clock_channel(100, "FIO0")
    device.start_clocks()
finally:
    device.close()  # Ensure cleanup
```

## Device Implementations

### `LabJackT4`

LabJack T4 USB DAQ device implementation.

```python
class LabJackT4(ClockDaqDevice):
    """
    XClock driver for LabJack T4 device.
    
    Attributes:
        base_clock_frequency_hz: 80,000,000 (80 MHz)
        handle: LabJack device handle
    """
```

**Specifications:**
- Base clock: 80 MHz
- Output channels: FIO0-7, EIO0-3 (12 total)
- Trigger input: DIO4
- Frequency range: ~1 Hz to ~40 MHz
- Timing precision: < 1 µs jitter

**Example:**
```python
from xclock.devices import LabJackT4

t4 = LabJackT4()
print(f"Base clock: {t4.base_clock_frequency_hz} Hz")

# Use all features
t4.add_clock_channel(100, "FIO0", duration_s=10)
t4.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    filename="timestamps.csv"
)
t4.close()
```

### `DummyDaqDevice`

Software-only device for testing without hardware.

```python
class DummyDaqDevice(ClockDaqDevice):
    """
    Dummy DAQ device for testing.
    
    Simulates all functionality without requiring hardware.
    Useful for development, testing, and demonstrations.
    """
```

**Features:**
- No hardware required
- Same API as real devices
- Simulated timestamps
- Configurable behavior

**Example:**
```python
from xclock.devices import DummyDaqDevice

dummy = DummyDaqDevice()
dummy.add_clock_channel(100, duration_s=5)
dummy.start_clocks(wait_for_pulsed_clocks_to_finish=True)
dummy.close()

print("Test completed without hardware!")
```

## Data Classes

### `ClockChannel`

Represents a configured clock channel.

```python
@dataclass
class ClockChannel:
    """
    Configuration and state of a clock channel.
    
    Attributes:
        channel_name: Output channel name (e.g., "FIO0")
        clock_id: Unique identifier (1, 2, 3, ...)
        clock_enabled: Whether clock is currently running
        actual_sample_rate_hz: Actual achieved frequency
        number_of_pulses: Number of pulses (None = continuous)
    """
    channel_name: str
    clock_id: int
    clock_enabled: bool
    actual_sample_rate_hz: int
    number_of_pulses: int | None = None
```

**Example:**
```python
device = LabJackT4()
clock = device.add_clock_channel(100, "FIO0", number_of_pulses=1000)

print(f"Channel: {clock.channel_name}")
print(f"Requested: 100 Hz")
print(f"Actual: {clock.actual_sample_rate_hz} Hz")
print(f"Pulses: {clock.number_of_pulses}")
print(f"Enabled: {clock.clock_enabled}")
```

## Enumerations

### `EdgeType`

Enumeration for edge types in trigger detection.

```python
class EdgeType(Enum):
    """
    Type of edge for trigger detection.
    
    Values:
        RISING: Rising edge (low to high)
        FALLING: Falling edge (high to low)
    """
    RISING = "rising"
    FALLING = "falling"
```

**Example:**
```python
from xclock.devices import EdgeType

device = LabJackT4()
device.add_clock_channel(100, "FIO0", duration_s=10)

# Wait for rising edge
device.wait_for_trigger_edge("DIO4", edge_type=EdgeType.RISING)
device.start_clocks()
```

## Complete Example

```python
from pathlib import Path
import numpy as np
from xclock.devices import LabJackT4, EdgeType

# Initialize device
device = LabJackT4()

try:
    # Check available resources
    output_channels = device.get_available_output_clock_channels()
    trigger_channels = device.get_available_input_start_trigger_channels()
    
    print(f"Output channels: {output_channels}")
    print(f"Trigger channels: {trigger_channels}")
    
    # Configure multiple synchronized clocks
    clock1 = device.add_clock_channel(
        clock_tick_rate_hz=60,
        channel_name="FIO0",
        duration_s=30.0,  # 30 seconds
    )
    
    clock2 = device.add_clock_channel(
        clock_tick_rate_hz=100,
        channel_name="FIO1",
        duration_s=30.0,
    )
    
    print(f"Clock 1: {clock1.actual_sample_rate_hz} Hz on {clock1.channel_name}")
    print(f"Clock 2: {clock2.actual_sample_rate_hz} Hz on {clock2.channel_name}")
    
    # Wait for external trigger
    print("Waiting for trigger on DIO4...")
    triggered = device.wait_for_trigger_edge(
        channel_name="DIO4",
        timeout_s=60.0,
        edge_type=EdgeType.RISING,
    )
    
    if not triggered:
        print("Timeout - exiting")
        exit(1)
    
    print("Trigger received! Starting clocks and recording...")
    
    # Start clocks and record timestamps
    output_file = Path.home() / "Documents" / "XClock" / "experiment.csv"
    device.start_clocks_and_record_edge_timestamps(
        wait_for_pulsed_clocks_to_finish=True,
        filename=output_file,
    )
    
    print(f"Recording complete: {output_file}")
    
    # Load and analyze timestamps
    data = np.loadtxt(output_file, dtype=np.int64, delimiter=",")
    timestamps_ns = data[:, 0]       # Device-relative timestamps
    edge_types = data[:, 1]          # Edge type
    unix_timestamps_ns = data[:, 2]  # Unix timestamps (host time)
    
    # Count edges per clock
    clock1_rising = np.sum(edge_types == 1)
    clock1_falling = np.sum(edge_types == -1)
    clock2_rising = np.sum(edge_types == 2)
    clock2_falling = np.sum(edge_types == -2)
    
    print(f"Clock 1: {clock1_rising} rising, {clock1_falling} falling")
    print(f"Clock 2: {clock2_rising} rising, {clock2_falling} falling")
    
finally:
    # Always clean up
    device.close()
    print("Device closed")
```

## See Also

- {doc}`../user/quickstart` - Getting started guide
- {doc}`../user/devices` - Device-specific information
- {doc}`../developer/adding_devices` - Adding new devices
- {doc}`edge_detection` - Edge detection API
- {doc}`errors` - Error handling