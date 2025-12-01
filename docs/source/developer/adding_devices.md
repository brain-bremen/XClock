# Adding New Device Support

This guide explains how to add support for a new DAQ device to XClock. Following this guide, you can extend XClock to work with any data acquisition hardware that can generate clock signals.

## Overview

Adding a new device involves:

1. Creating a new device class that implements the `ClockDaqDevice` interface
2. Implementing all required abstract methods
3. Writing tests for your device
4. Documenting device-specific features
5. Registering the device in the CLI (optional)

## Prerequisites

Before you start:

- Familiarity with Python object-oriented programming
- Understanding of your DAQ device's API/SDK
- The device's driver/SDK installed and working
- XClock development environment set up

## Step 1: Understand the Interface

All clock devices must inherit from the `ClockDaqDevice` abstract base class and implement its interface.

### Required Interface

```python
from abc import ABC, abstractmethod
from xclock.devices.daq_device import ClockDaqDevice, ClockChannel, EdgeType

class ClockDaqDevice(ABC):
    """Abstract base class for all clock DAQ devices."""
    
    handle: int | None
    base_clock_frequency_hz: int | float
    
    @staticmethod
    @abstractmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        """Return tuple of channel names that can be used as trigger inputs."""
        pass
    
    @staticmethod
    @abstractmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        """Return tuple of channel names that can output clock signals."""
        pass
    
    @abstractmethod
    def get_added_clock_channels(self) -> list[ClockChannel]:
        """Return list of currently configured clock channels."""
        pass
    
    @abstractmethod
    def get_unused_clock_channel_names(self) -> list[str]:
        """Return list of available (not yet used) channel names."""
        pass
    
    @abstractmethod
    def add_clock_channel(
        self,
        clock_tick_rate_hz: int | float,
        channel_name: str | None = None,
        number_of_pulses: int | None = None,
        duration_s: float | None = None,
        enable_clock_now: bool = False,
    ) -> ClockChannel:
        """Configure a new clock channel."""
        pass
    
    @abstractmethod
    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        """Wait for trigger signal. Returns True if triggered, False if timeout."""
        pass
    
    @abstractmethod
    def start_clocks(
        self,
        wait_for_pulsed_clocks_to_finish: bool = False,
    ):
        """Start all configured clocks."""
        pass
    
    @abstractmethod
    def start_clocks_and_record_edge_timestamps(
        self,
        wait_for_pulsed_clocks_to_finish: bool = True,
        extra_channels: list[str] = [],
        filename: Path | str | None = None,
    ):
        """Start clocks and record edge timestamps to CSV file."""
        pass
    
    @abstractmethod
    def stop_clocks(self):
        """Stop all running clocks."""
        pass
    
    @abstractmethod
    def clear_clocks(self):
        """Remove all configured clocks."""
        pass
    
    @abstractmethod
    def close(self):
        """Clean up resources and close device connection."""
        pass
```

## Step 2: Create Your Device Class

Create a new file in `src/xclock/devices/` for your device. For example, `my_daq_device.py`:

```python
from pathlib import Path
import logging
from xclock.devices.daq_device import ClockDaqDevice, ClockChannel, EdgeType
from xclock.errors import XClockException

logger = logging.getLogger(__name__)


class MyDAQDevice(ClockDaqDevice):
    """
    XClock driver for MyDAQ Device.
    
    This device supports:
    - Base clock frequency: 100 MHz
    - 4 output channels (CH0-CH3)
    - 1 trigger input (TRIG0)
    - Hardware-synchronized multi-channel output
    
    Example:
        >>> device = MyDAQDevice()
        >>> device.add_clock_channel(clock_tick_rate_hz=100, channel_name="CH0")
        >>> device.start_clocks()
        >>> device.close()
    """
    
    def __init__(self):
        """Initialize MyDAQ device."""
        self.handle = None
        self.base_clock_frequency_hz = 100_000_000  # 100 MHz
        self._clock_channels = []
        
        # Initialize your device here
        try:
            # Example: Open device connection
            # self.handle = mydaq_sdk.open_device()
            logger.info("MyDAQ device initialized successfully")
        except Exception as e:
            raise XClockException(f"Failed to initialize MyDAQ: {e}")
    
    @staticmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        """Return available output channels."""
        return ("CH0", "CH1", "CH2", "CH3")
    
    @staticmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        """Return available trigger input channels."""
        return ("TRIG0",)
    
    def get_added_clock_channels(self) -> list[ClockChannel]:
        """Return list of configured clock channels."""
        return self._clock_channels.copy()
    
    def get_unused_clock_channel_names(self) -> list[str]:
        """Return list of unused channel names."""
        used_names = {ch.channel_name for ch in self._clock_channels}
        all_names = set(self.get_available_output_clock_channels())
        return list(all_names - used_names)
    
    def add_clock_channel(
        self,
        clock_tick_rate_hz: int | float,
        channel_name: str | None = None,
        number_of_pulses: int | None = None,
        duration_s: float | None = None,
        enable_clock_now: bool = False,
    ) -> ClockChannel:
        """
        Add a new clock channel.
        
        Args:
            clock_tick_rate_hz: Desired clock frequency in Hz
            channel_name: Output channel name (or None for auto-select)
            number_of_pulses: Number of pulses (None = continuous)
            duration_s: Duration in seconds (auto-calculates pulses)
            enable_clock_now: Start immediately if True
        
        Returns:
            ClockChannel object with actual configuration
        """
        # Auto-select channel if not specified
        if channel_name is None:
            unused = self.get_unused_clock_channel_names()
            if not unused:
                raise XClockException("No available channels")
            channel_name = unused[0]
        
        # Validate channel name
        if channel_name not in self.get_available_output_clock_channels():
            raise XClockException(f"Invalid channel: {channel_name}")
        
        # Check if channel already in use
        if channel_name in [ch.channel_name for ch in self._clock_channels]:
            raise XClockException(f"Channel {channel_name} already in use")
        
        # Calculate pulses from duration if needed
        if duration_s is not None and number_of_pulses is None:
            number_of_pulses = int(duration_s * clock_tick_rate_hz)
        
        # Calculate actual achievable frequency
        # This is device-specific - adjust for your hardware
        actual_frequency = self._calculate_actual_frequency(clock_tick_rate_hz)
        
        # Create clock channel object
        clock_id = len(self._clock_channels) + 1
        channel = ClockChannel(
            channel_name=channel_name,
            clock_id=clock_id,
            clock_enabled=enable_clock_now,
            actual_sample_rate_hz=actual_frequency,
            number_of_pulses=number_of_pulses,
        )
        
        self._clock_channels.append(channel)
        
        # Configure hardware
        self._configure_hardware_clock(channel)
        
        logger.info(f"Added clock: {actual_frequency} Hz on {channel_name}")
        return channel
    
    def _calculate_actual_frequency(self, requested_hz: float) -> int:
        """
        Calculate actual achievable frequency given device constraints.
        
        This is device-specific. Implement based on your hardware's
        clock generation mechanism (divisors, PLLs, etc.).
        """
        # Example: Simple divisor-based calculation
        divisor = round(self.base_clock_frequency_hz / requested_hz)
        divisor = max(1, divisor)  # Ensure at least 1
        actual_hz = self.base_clock_frequency_hz / divisor
        return int(actual_hz)
    
    def _configure_hardware_clock(self, channel: ClockChannel):
        """Configure hardware registers/settings for this clock."""
        # Implement device-specific configuration here
        # Example:
        # mydaq_sdk.configure_clock(
        #     self.handle,
        #     channel.channel_name,
        #     channel.actual_sample_rate_hz,
        #     channel.number_of_pulses
        # )
        pass
    
    def start_clocks(self, wait_for_pulsed_clocks_to_finish: bool = False):
        """Start all configured clocks."""
        if not self._clock_channels:
            raise XClockException("No clocks configured")
        
        logger.info(f"Starting {len(self._clock_channels)} clocks")
        
        # Start clocks on hardware
        # Example:
        # mydaq_sdk.start_all_clocks(self.handle)
        
        # Mark all as enabled
        for channel in self._clock_channels:
            channel.clock_enabled = True
        
        # Wait if requested
        if wait_for_pulsed_clocks_to_finish:
            self._wait_for_completion()
    
    def _wait_for_completion(self):
        """Wait for pulsed clocks to finish."""
        # Implement waiting logic
        # Example:
        # while mydaq_sdk.is_running(self.handle):
        #     time.sleep(0.1)
        pass
    
    def stop_clocks(self):
        """Stop all running clocks."""
        logger.info("Stopping all clocks")
        
        # Stop hardware
        # Example:
        # mydaq_sdk.stop_all_clocks(self.handle)
        
        # Mark all as disabled
        for channel in self._clock_channels:
            channel.clock_enabled = False
    
    def clear_clocks(self):
        """Remove all configured clocks."""
        self.stop_clocks()
        self._clock_channels.clear()
        logger.info("Cleared all clocks")
    
    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        """
        Wait for trigger signal on specified channel.
        
        Returns:
            True if triggered, False if timeout
        """
        if channel_name not in self.get_available_input_start_trigger_channels():
            raise XClockException(f"Invalid trigger channel: {channel_name}")
        
        logger.info(f"Waiting for {edge_type.value} edge on {channel_name}")
        
        # Implement trigger waiting
        # Example:
        # return mydaq_sdk.wait_for_edge(
        #     self.handle, 
        #     channel_name,
        #     edge_type.value,
        #     timeout_s
        # )
        
        return True  # Placeholder
    
    def start_clocks_and_record_edge_timestamps(
        self,
        wait_for_pulsed_clocks_to_finish: bool = True,
        extra_channels: list[str] = [],
        filename: Path | str | None = None,
    ):
        """Start clocks and record edge timestamps to CSV file."""
        # This is complex - see LabJackT4 implementation for reference
        # You may need to implement a separate edge streamer class
        
        # Generate default filename if not provided
        if filename is None:
            import time
            output_dir = Path.home() / "Documents" / "XClock"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
            filename = output_dir / f"mydaq_timestamps_{timestamp_str}.csv"
        
        # Start recording and clocks
        # This typically requires:
        # 1. Start edge detection on all clock channels + extra_channels
        # 2. Start clocks
        # 3. Record timestamps
        # 4. Save to CSV
        
        raise NotImplementedError("Timestamp recording not yet implemented")
    
    def close(self):
        """Clean up and close device."""
        if self.handle is not None:
            self.stop_clocks()
            
            # Close device connection
            # Example:
            # mydaq_sdk.close_device(self.handle)
            
            logger.info("MyDAQ device closed")
            self.handle = None
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except:
            pass
```

## Step 3: Write Tests

Create a test file `tests/xclock/test_my_daq.py`:

```python
import pytest
from xclock.devices.my_daq_device import MyDAQDevice
from xclock.devices.daq_device import EdgeType


# Set these for your device
DEVICE_NAME = "MyDAQ"
DEVICE_CLASS = MyDAQDevice


def test_device_initialization():
    """Test that device initializes successfully."""
    device = DEVICE_CLASS()
    assert device is not None
    assert device.handle is not None
    device.close()


def test_get_available_channels():
    """Test that device reports available channels."""
    output_channels = DEVICE_CLASS.get_available_output_clock_channels()
    assert len(output_channels) > 0
    assert all(isinstance(ch, str) for ch in output_channels)
    
    trigger_channels = DEVICE_CLASS.get_available_input_start_trigger_channels()
    assert len(trigger_channels) >= 0  # May be 0 if no trigger support


def test_add_clock_channel():
    """Test adding a clock channel."""
    device = DEVICE_CLASS()
    channels = device.get_available_output_clock_channels()
    
    clock = device.add_clock_channel(
        clock_tick_rate_hz=100,
        channel_name=channels[0],
        number_of_pulses=1000,
    )
    
    assert clock is not None
    assert clock.channel_name == channels[0]
    assert clock.actual_sample_rate_hz > 0
    assert clock.number_of_pulses == 1000
    
    device.close()


def test_multiple_clocks():
    """Test adding multiple synchronized clocks."""
    device = DEVICE_CLASS()
    channels = device.get_available_output_clock_channels()
    
    if len(channels) < 2:
        pytest.skip("Device has fewer than 2 channels")
    
    clock1 = device.add_clock_channel(60, channels[0], number_of_pulses=100)
    clock2 = device.add_clock_channel(100, channels[1], number_of_pulses=100)
    
    assert clock1.channel_name != clock2.channel_name
    assert len(device.get_added_clock_channels()) == 2
    
    device.close()


def test_start_stop_clocks():
    """Test starting and stopping clocks."""
    device = DEVICE_CLASS()
    channels = device.get_available_output_clock_channels()
    
    device.add_clock_channel(100, channels[0], number_of_pulses=10)
    
    # Should not raise
    device.start_clocks(wait_for_pulsed_clocks_to_finish=False)
    device.stop_clocks()
    
    device.close()


def test_clear_clocks():
    """Test clearing all clocks."""
    device = DEVICE_CLASS()
    channels = device.get_available_output_clock_channels()
    
    device.add_clock_channel(100, channels[0])
    assert len(device.get_added_clock_channels()) == 1
    
    device.clear_clocks()
    assert len(device.get_added_clock_channels()) == 0
    
    device.close()


def test_auto_channel_selection():
    """Test automatic channel selection."""
    device = DEVICE_CLASS()
    
    # Don't specify channel_name
    clock = device.add_clock_channel(clock_tick_rate_hz=100)
    
    assert clock.channel_name in device.get_available_output_clock_channels()
    
    device.close()


def test_duration_pulse_calculation():
    """Test that duration correctly calculates pulses."""
    device = DEVICE_CLASS()
    
    clock = device.add_clock_channel(
        clock_tick_rate_hz=100,
        duration_s=5.0,  # 5 seconds at 100 Hz = 500 pulses
    )
    
    assert clock.number_of_pulses == 500
    
    device.close()


def test_unused_channels():
    """Test getting unused channel names."""
    device = DEVICE_CLASS()
    channels = device.get_available_output_clock_channels()
    
    # Initially all unused
    unused = device.get_unused_clock_channel_names()
    assert len(unused) == len(channels)
    
    # Add one clock
    device.add_clock_channel(100, channels[0])
    unused = device.get_unused_clock_channel_names()
    assert len(unused) == len(channels) - 1
    assert channels[0] not in unused
    
    device.close()


def test_close_cleanup():
    """Test that close() properly cleans up."""
    device = DEVICE_CLASS()
    device.add_clock_channel(100)
    device.close()
    
    # After close, handle should be None
    assert device.handle is None
```

## Step 4: Register in CLI (Optional)

If you want your device to be available in the CLI, add it to `src/cli/main.py`:

```python
from xclock.devices import ClockDaqDevice, DummyDaqDevice, LabJackT4
from xclock.devices.my_daq_device import MyDAQDevice  # Add import

# Device mapping
DEVICE_MAP = {
    "labjackt4": LabJackT4,
    "dummydaqdevice": DummyDaqDevice,
    "mydaqdevice": MyDAQDevice,  # Add your device
}
```

## Step 5: Update Package Exports

Add your device to `src/xclock/devices/__init__.py`:

```python
from xclock.devices.daq_device import ClockDaqDevice
from xclock.devices.labjack_devices import LabJackT4
from xclock.devices.dummy_daq_device import DummyDaqDevice
from xclock.devices.my_daq_device import MyDAQDevice  # Add import

__all__ = [
    "ClockDaqDevice",
    "LabJackT4",
    "DummyDaqDevice",
    "MyDAQDevice",  # Add to exports
]
```

## Step 6: Document Your Device

Add documentation in `docs/source/user/devices.md`:

```markdown
### MyDAQ Device

Brief description of your device.

**Specifications:**
- Base clock frequency: 100 MHz
- Available output channels: 4 (CH0-CH3)
- Trigger input: TRIG0
- ...

**Example:**

\```python
from xclock.devices import MyDAQDevice

device = MyDAQDevice()
device.add_clock_channel(clock_tick_rate_hz=100, channel_name="CH0")
device.start_clocks()
device.close()
\```
```

## Best Practices

### Error Handling

Always use `XClockException` for device-specific errors:

```python
from xclock.errors import XClockException

if not self.handle:
    raise XClockException("Device not initialized")
```

### Logging

Use Python's logging module:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Device initialized")
logger.debug(f"Clock configured: {channel_name} at {frequency} Hz")
logger.warning("Frequency adjusted to nearest achievable value")
logger.error("Failed to start clock")
```

### Resource Cleanup

Always implement cleanup in `close()` and `__del__()`:

```python
def close(self):
    """Clean up resources."""
    if self.handle is not None:
        self.stop_clocks()
        # Close device connection
        self.handle = None

def __del__(self):
    """Ensure cleanup on deletion."""
    try:
        self.close()
    except:
        pass
```

### Type Hints

Use type hints for better IDE support and documentation:

```python
def add_clock_channel(
    self,
    clock_tick_rate_hz: int | float,
    channel_name: str | None = None,
    number_of_pulses: int | None = None,
) -> ClockChannel:
    ...
```

## Advanced Features

### Timestamp Recording

For precise timestamp recording, you may need to implement a streaming class similar to `LabJackEdgeStreamer`. This typically involves:

1. Starting continuous data acquisition
2. Processing incoming data in real-time
3. Detecting edges
4. Recording timestamps
5. Saving to CSV format

See `LabJackEdgeStreamer` in `labjack_devices.py` for a complete example.

### Hardware Synchronization

If your device supports hardware-synchronized multi-channel output:

1. Configure all channels before starting
2. Use hardware trigger to start all simultaneously
3. Ensure all channels reference the same base clock

### Frequency Calculation

Different devices have different clock generation methods:

- **Divisor-based**: Frequency = BaseClk / Divisor
- **PLL-based**: More complex calculations
- **DDS-based**: Direct digital synthesis

Implement `_calculate_actual_frequency()` based on your hardware.

## Testing Checklist

Before submitting your device implementation:

- [ ] All abstract methods implemented
- [ ] Unit tests written and passing
- [ ] Device can be initialized
- [ ] Clocks can be added, started, and stopped
- [ ] Multiple clocks work simultaneously
- [ ] Trigger functionality works (if applicable)
- [ ] Resources cleaned up properly
- [ ] Documentation added
- [ ] CLI integration (optional)
- [ ] Example code provided

## Common Pitfalls

### 1. Not Handling Resource Cleanup

Always close device connections in `close()` and `__del__()`.

### 2. Ignoring Frequency Limitations

Not all frequencies are achievable. Calculate and return the actual frequency.

### 3. Thread Safety

If using threading (e.g., for timestamp recording), ensure thread-safe operations.

### 4. Hardware State

Track hardware state (started/stopped) to avoid conflicts.

### 5. Channel Validation

Always validate channel names against available channels.

## Example: Complete Minimal Device

Here's a minimal but complete device implementation:

```python
from pathlib import Path
from xclock.devices.daq_device import ClockDaqDevice, ClockChannel, EdgeType
from xclock.errors import XClockException


class MinimalDevice(ClockDaqDevice):
    """Minimal device implementation for reference."""
    
    def __init__(self):
        self.handle = 1  # Dummy handle
        self.base_clock_frequency_hz = 1_000_000
        self._clocks = []
    
    @staticmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        return ("CH0", "CH1")
    
    @staticmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        return ("TRIG0",)
    
    def get_added_clock_channels(self) -> list[ClockChannel]:
        return self._clocks.copy()
    
    def get_unused_clock_channel_names(self) -> list[str]:
        used = {c.channel_name for c in self._clocks}
        return [ch for ch in self.get_available_output_clock_channels() if ch not in used]
    
    def add_clock_channel(self, clock_tick_rate_hz, channel_name=None, 
                         number_of_pulses=None, duration_s=None, enable_clock_now=False):
        if channel_name is None:
            channel_name = self.get_unused_clock_channel_names()[0]
        
        if duration_s and not number_of_pulses:
            number_of_pulses = int(duration_s * clock_tick_rate_hz)
        
        channel = ClockChannel(
            channel_name=channel_name,
            clock_id=len(self._clocks) + 1,
            clock_enabled=enable_clock_now,
            actual_sample_rate_hz=int(clock_tick_rate_hz),
            number_of_pulses=number_of_pulses,
        )
        self._clocks.append(channel)
        return channel
    
    def start_clocks(self, wait_for_pulsed_clocks_to_finish=False):
        for c in self._clocks:
            c.clock_enabled = True
    
    def stop_clocks(self):
        for c in self._clocks:
            c.clock_enabled = False
    
    def clear_clocks(self):
        self._clocks.clear()
    
    def wait_for_trigger_edge(self, channel_name, timeout_s=5.0, edge_type=EdgeType.RISING):
        return True
    
    def start_clocks_and_record_edge_timestamps(self, wait_for_pulsed_clocks_to_finish=True,
                                                extra_channels=[], filename=None):
        self.start_clocks(wait_for_pulsed_clocks_to_finish)
    
    def close(self):
        self.stop_clocks()
        self.handle = None
```

## Getting Help

If you need help adding a new device:

1. Check the `LabJackT4` implementation as a reference
2. Review the `DummyDaqDevice` for a simpler example
3. Open an issue on GitHub with the device details
4. Join the discussion in the developer community

## See Also

- {doc}`../api/devices` - API reference
- Example: `src/xclock/devices/labjack_devices.py`
- Example: `src/xclock/devices/dummy_daq_device.py`
