# Errors API Reference

This page documents the exception classes used in XClock for error handling.

## Overview

XClock defines a hierarchy of exception classes for handling different types of errors that may occur during device operation. All XClock exceptions inherit from a common base class, making it easy to catch all XClock-related errors.

```python
from xclock.errors import XClockException, XClockValueError
```

## Exception Hierarchy

```
Exception (built-in)
└── XClockException
    ├── XClockValueError
    ├── XClockDeviceError
    └── XClockTimeoutError
```

## Exception Classes

### `XClockException`

Base exception class for all XClock errors.

```python
class XClockException(Exception):
    """
    Base exception for all XClock errors.
    
    This is the parent class for all XClock-specific exceptions.
    Catching this exception will catch all XClock errors.
    """
```

**Usage:**

Use this to catch any XClock-related error:

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockException

try:
    device = LabJackT4()
    device.add_clock_channel(clock_tick_rate_hz=100)
    device.start_clocks()
except XClockException as e:
    print(f"XClock error occurred: {e}")
finally:
    device.close()
```

### `XClockValueError`

Raised when invalid values or parameters are provided.

```python
class XClockValueError(XClockException):
    """
    Exception raised for invalid parameter values.
    
    This exception is raised when a parameter value is invalid,
    out of range, or conflicts with other parameters.
    """
```

**Common Causes:**

- Invalid frequency values (negative, zero, or out of range)
- Invalid channel names
- Conflicting parameters (e.g., both `duration_s` and `number_of_pulses` specified)
- Invalid configuration combinations

**Examples:**

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockValueError

device = LabJackT4()

# Example 1: Invalid frequency
try:
    device.add_clock_channel(clock_tick_rate_hz=-100)  # Negative frequency
except XClockValueError as e:
    print(f"Invalid value: {e}")

# Example 2: Invalid channel name
try:
    device.add_clock_channel(
        clock_tick_rate_hz=100,
        channel_name="INVALID_CHANNEL"
    )
except XClockValueError as e:
    print(f"Invalid channel: {e}")

# Example 3: Conflicting parameters
try:
    device.add_clock_channel(
        clock_tick_rate_hz=100,
        duration_s=10.0,
        number_of_pulses=500  # Can't specify both
    )
except XClockValueError as e:
    print(f"Parameter conflict: {e}")

device.close()
```

### `XClockDeviceError`

Raised when device-level errors occur.

```python
class XClockDeviceError(XClockException):
    """
    Exception raised for device-level errors.
    
    This exception is raised when there are problems communicating
    with or controlling the hardware device.
    """
```

**Common Causes:**

- Device not found or not connected
- USB communication errors
- Device initialization failures
- Hardware malfunction
- Driver/SDK errors

**Examples:**

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockDeviceError

# Example 1: Device not connected
try:
    device = LabJackT4()  # No device connected
except XClockDeviceError as e:
    print(f"Device error: {e}")
    print("Please check USB connection")

# Example 2: Communication error during operation
try:
    device = LabJackT4()
    device.add_clock_channel(100, "FIO0")
    device.start_clocks()
    # ... device unplugged during operation ...
except XClockDeviceError as e:
    print(f"Device communication error: {e}")
```

### `XClockTimeoutError`

Raised when an operation times out.

```python
class XClockTimeoutError(XClockException):
    """
    Exception raised when an operation times out.
    
    This exception is raised when a time-limited operation
    does not complete within the specified timeout period.
    """
```

**Common Causes:**

- Waiting for trigger that never arrives
- Device not responding
- Long-running operations exceeding timeout

**Examples:**

```python
from xclock.devices import LabJackT4, EdgeType
from xclock.errors import XClockTimeoutError

device = LabJackT4()

# Example 1: Trigger timeout
try:
    triggered = device.wait_for_trigger_edge(
        channel_name="DIO4",
        timeout_s=10.0,
        edge_type=EdgeType.RISING,
    )
    if not triggered:
        print("No trigger received within 10 seconds")
except XClockTimeoutError as e:
    print(f"Timeout error: {e}")

device.close()
```

## Error Handling Patterns

### Pattern 1: Catch All XClock Errors

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockException

try:
    device = LabJackT4()
    device.add_clock_channel(100, "FIO0", duration_s=10)
    device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
except XClockException as e:
    print(f"XClock error: {e}")
    # Handle any XClock error
finally:
    try:
        device.close()
    except:
        pass
```

### Pattern 2: Handle Specific Errors Differently

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockValueError, XClockDeviceError, XClockTimeoutError

try:
    device = LabJackT4()
    device.add_clock_channel(100, "FIO0")
    
    # Wait for trigger
    triggered = device.wait_for_trigger_edge("DIO4", timeout_s=30.0)
    if triggered:
        device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
    
except XClockValueError as e:
    print(f"Configuration error: {e}")
    print("Please check your parameters")
    
except XClockDeviceError as e:
    print(f"Device error: {e}")
    print("Please check device connection and drivers")
    
except XClockTimeoutError as e:
    print(f"Timeout: {e}")
    print("Operation took too long")
    
finally:
    device.close()
```

### Pattern 3: Retry on Specific Errors

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockDeviceError
import time

MAX_RETRIES = 3
RETRY_DELAY = 2.0

for attempt in range(MAX_RETRIES):
    try:
        device = LabJackT4()
        print("Device connected successfully")
        break
    except XClockDeviceError as e:
        if attempt < MAX_RETRIES - 1:
            print(f"Connection failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            print(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
        else:
            print(f"Failed to connect after {MAX_RETRIES} attempts")
            raise
```

### Pattern 4: Graceful Degradation

```python
from xclock.devices import LabJackT4, DummyDaqDevice
from xclock.errors import XClockDeviceError

# Try real hardware, fall back to dummy device
try:
    device = LabJackT4()
    print("Using LabJack T4 hardware")
except XClockDeviceError:
    print("Hardware not available, using dummy device")
    device = DummyDaqDevice()

# Rest of code works the same
device.add_clock_channel(100, duration_s=5)
device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
device.close()
```

### Pattern 5: Context Manager (if implemented)

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockException

try:
    # Assuming context manager support
    with LabJackT4() as device:
        device.add_clock_channel(100, "FIO0", duration_s=10)
        device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
except XClockException as e:
    print(f"Error: {e}")
# Device automatically closed
```

## Best Practices

### 1. Always Close Devices

Even when errors occur, ensure devices are properly closed:

```python
device = None
try:
    device = LabJackT4()
    # ... operations ...
except XClockException as e:
    print(f"Error: {e}")
finally:
    if device is not None:
        try:
            device.close()
        except:
            pass  # Ignore errors during cleanup
```

### 2. Provide Context in Error Messages

When re-raising or wrapping exceptions:

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockException

def setup_experiment(frequencies):
    """Setup experiment with multiple clocks."""
    try:
        device = LabJackT4()
        for i, freq in enumerate(frequencies):
            device.add_clock_channel(freq)
        return device
    except XClockException as e:
        raise XClockException(
            f"Failed to setup experiment with frequencies {frequencies}: {e}"
        ) from e
```

### 3. Log Errors Appropriately

```python
import logging
from xclock.devices import LabJackT4
from xclock.errors import XClockException

logger = logging.getLogger(__name__)

try:
    device = LabJackT4()
    device.add_clock_channel(100, "FIO0")
    device.start_clocks()
except XClockException as e:
    logger.error(f"XClock operation failed: {e}", exc_info=True)
    raise
finally:
    device.close()
```

### 4. Validate Early

Validate parameters early to provide clear error messages:

```python
from xclock.errors import XClockValueError

def add_validated_clock(device, frequency, channel=None):
    """Add clock with validation."""
    # Validate frequency
    if frequency <= 0:
        raise XClockValueError(f"Frequency must be positive, got {frequency}")
    
    if frequency > 1_000_000:
        raise XClockValueError(f"Frequency too high: {frequency} Hz (max: 1 MHz)")
    
    # Validate channel if specified
    if channel is not None:
        available = device.get_available_output_clock_channels()
        if channel not in available:
            raise XClockValueError(
                f"Invalid channel '{channel}'. Available: {available}"
            )
    
    # Add clock
    return device.add_clock_channel(frequency, channel)
```

## Error Messages

XClock aims to provide clear, actionable error messages:

**Good error messages include:**
- What went wrong
- Why it happened (if known)
- How to fix it (if applicable)

**Examples:**

```
❌ Bad:  "Invalid parameter"
✅ Good: "Invalid frequency: -100 Hz. Frequency must be positive."

❌ Bad:  "Device error"
✅ Good: "Failed to connect to LabJack T4. Check USB connection and ensure drivers are installed."

❌ Bad:  "Can't add clock"
✅ Good: "Cannot add clock: channel 'FIO0' is already in use. Available channels: FIO1, FIO2, FIO3"
```

## Common Error Scenarios

### Scenario 1: Device Not Found

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockDeviceError

try:
    device = LabJackT4()
except XClockDeviceError as e:
    print("Troubleshooting steps:")
    print("1. Check USB cable is connected")
    print("2. Verify device power LED is on")
    print("3. Ensure LabJack LJM drivers are installed")
    print("4. Try a different USB port")
    print("5. Test device with Kipling software")
```

### Scenario 2: Invalid Configuration

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockValueError

device = LabJackT4()

try:
    # Trying to use more channels than available
    for i in range(20):  # Device only has 12 channels
        device.add_clock_channel(100)
except XClockValueError as e:
    print(f"Configuration error: {e}")
    print(f"Device supports up to {len(device.get_available_output_clock_channels())} channels")
```

### Scenario 3: Resource Cleanup Errors

```python
from xclock.devices import LabJackT4
from xclock.errors import XClockException

device = LabJackT4()
device.add_clock_channel(100, "FIO0")
device.start_clocks()

# Don't forget to stop and close!
try:
    device.stop_clocks()
    device.close()
except XClockException as e:
    print(f"Cleanup error: {e}")
    # May need to power cycle device
```

## See Also

- {doc}`devices` - Device API reference
- {doc}`edge_detection` - Edge detection API
- {doc}`../user/quickstart` - Usage examples