# Edge Detection API Reference

This page documents the edge detection and timestamp recording functionality in XClock.

## Overview

The edge detection module provides real-time monitoring and timestamp recording of digital signal edges. This is essential for synchronizing data acquisition across multiple devices by providing precise timing information.

```python
from xclock.edge_detection import detect_edges, process_timestamps
```

## Key Concepts

### Timestamp Recording

When recording timestamps, XClock:

1. Continuously streams data from input channels
2. Detects rising and falling edges in real-time
3. Calculates precise nanosecond timestamps
4. Handles hardware timer rollover
5. Writes timestamps to CSV files

### Edge Types

Edges are encoded as signed integers:

- **Positive integers** (1, 2, 3, ...): Rising edges on clock 1, 2, 3, ...
- **Negative integers** (-1, -2, -3, ...): Falling edges on clock 1, 2, 3, ...

### Timestamp Format

Timestamps are 64-bit integers representing nanoseconds since device start:

```
Timestamp (ns) = (Counter Value × 10^9) / Base Clock Frequency
Unix Timestamp (ns) = Host system time in nanoseconds since Unix epoch
```

## CSV Output Format

Timestamp files are saved as CSV with three columns:

| Column | Type | Description |
|--------|------|-------------|
| 0 | int64 | Timestamp in nanoseconds (relative to device start) |
| 1 | int8 | Edge type (positive=rising, negative=falling) |
| 2 | int64 | Unix timestamp in nanoseconds (host system time) |

**Example CSV content:**

```csv
1000000,1,1638360000000000000
1500000,-1,1638360000500000000
2000000,1,1638360001000000000
2500000,-1,1638360001500000000
2000000,2,1638360001000000000
2500000,-2,1638360001500000000
```

**Interpretation:**
- Line 1: Rising edge on clock 1 at 1.0 ms (device time), Unix timestamp in column 3
- Line 2: Falling edge on clock 1 at 1.5 ms (device time)
- Line 3: Rising edge on clock 1 at 2.0 ms (device time)
- Line 4: Falling edge on clock 1 at 2.5 ms (device time)
- Line 5: Rising edge on clock 2 at 2.0 ms (device time, synchronized with clock 1)
- Line 6: Falling edge on clock 2 at 2.5 ms (device time)

The Unix timestamp (column 2) provides the host system time when the edge was detected, useful for synchronizing with other systems or absolute time references.

## Device-Specific Implementation

### LabJack Edge Streaming

The LabJack T4 uses the `LabJackEdgeStreamer` class for continuous edge detection.

#### `LabJackEdgeStreamer`

```python
class LabJackEdgeStreamer:
    """
    Real-time edge detection and timestamp recording for LabJack devices.
    
    This class manages continuous streaming from LabJack input channels,
    detects edges, and records timestamps to a CSV file.
    
    Attributes:
        handle: LabJack device handle
        channels: List of channel names to monitor
        filename: Output CSV file path
        base_clock_hz: Device base clock frequency
    """
```

**Internal Operation:**

1. Configures LabJack streaming mode
2. Reads data buffers continuously
3. Processes timer values with rollover detection
4. Detects state changes (edges)
5. Calculates nanosecond timestamps
6. Writes to CSV file

**Threading:**
- Runs in background thread
- Thread-safe operation
- Graceful shutdown on stop

## Usage Examples

### Basic Timestamp Recording

```python
from xclock.devices import LabJackT4
from pathlib import Path

device = LabJackT4()

# Add clocks
device.add_clock_channel(100, "FIO0", duration_s=10)
device.add_clock_channel(60, "FIO1", duration_s=10)

# Record timestamps
output = Path("timestamps.csv")
device.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    filename=output,
)

device.close()
```

### Monitoring Additional Channels

```python
from xclock.devices import LabJackT4

device = LabJackT4()

# Add clock channels
device.add_clock_channel(100, "FIO0", duration_s=5)

# Also monitor external signals
device.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    extra_channels=["EIO4", "EIO5"],  # Monitor these too
    filename="all_edges.csv",
)

device.close()
```

### Analyzing Recorded Timestamps

```python
import numpy as np
from pathlib import Path

# Load timestamp data
data = np.loadtxt("timestamps.csv", dtype=np.int64, delimiter=",")
timestamps_ns = data[:, 0]  # Device-relative timestamps
edge_types = data[:, 1]     # Edge type
unix_timestamps_ns = data[:, 2]  # Unix timestamps (host time)

# Extract clock 1 rising edges
clock1_rising_times = timestamps_ns[edge_types == 1]

# Calculate inter-pulse intervals
intervals_ns = np.diff(clock1_rising_times)
intervals_us = intervals_ns / 1000  # Convert to microseconds

print(f"Mean interval: {np.mean(intervals_us):.2f} μs")
print(f"Std deviation: {np.std(intervals_us):.2f} μs")

# Expected interval for 100 Hz clock
expected_us = 1_000_000 / 100  # 10,000 μs
print(f"Expected: {expected_us:.2f} μs")

# Check timing accuracy
tolerance_us = 1.0  # 1 microsecond tolerance
accurate = np.all(np.abs(intervals_us - expected_us) < tolerance_us)
print(f"All intervals within tolerance: {accurate}")
```

### Separating Clocks

```python
import numpy as np

# Load data
data = np.loadtxt("timestamps.csv", dtype=np.int64, delimiter=",")
timestamps_ns = data[:, 0]
edge_types = data[:, 1]

# Separate by clock
clock1_mask = np.abs(edge_types) == 1
clock2_mask = np.abs(edge_types) == 2

clock1_times = timestamps_ns[clock1_mask]
clock1_edges = edge_types[clock1_mask]

clock2_times = timestamps_ns[clock2_mask]
clock2_edges = edge_types[clock2_mask]

print(f"Clock 1: {len(clock1_times)} edges")
print(f"Clock 2: {len(clock2_times)} edges")

# Find simultaneous events (within 1 μs)
tolerance_ns = 1000
for t1 in clock1_times:
    nearby = clock2_times[np.abs(clock2_times - t1) < tolerance_ns]
    if len(nearby) > 0:
        print(f"Simultaneous event at {t1} ns")
```

### Detecting Missed Pulses

```python
import numpy as np

# Load data
data = np.loadtxt("timestamps.csv", dtype=np.int64, delimiter=",")
timestamps_ns = data[:, 0]
edge_types = data[:, 1]

# Extract rising edges for 100 Hz clock
rising_edges = timestamps_ns[edge_types == 1]
intervals_ns = np.diff(rising_edges)

# Expected interval (in ns)
expected_ns = 1_000_000_000 / 100  # 10,000,000 ns

# Find intervals significantly larger than expected (missed pulses)
tolerance = 0.1  # 10% tolerance
missed = intervals_ns > expected_ns * (1 + tolerance)

if np.any(missed):
    print(f"Warning: {np.sum(missed)} potential missed pulses detected")
    missed_indices = np.where(missed)[0]
    for idx in missed_indices:
        print(f"  Gap between pulse {idx} and {idx+1}: {intervals_ns[idx]/1e6:.2f} ms")
else:
    print("No missed pulses detected")
```

## Rollover Handling

Hardware timers are typically 32-bit, causing rollover every ~53 seconds (for 80 MHz clock):

```
Rollover Period = 2^32 / 80,000,000 Hz ≈ 53.687 seconds
```

XClock automatically detects and handles rollover:

```python
def handle_rollover(current_value, previous_value, max_value=2**32):
    """
    Detect and compensate for timer rollover.
    
    Args:
        current_value: Current timer reading
        previous_value: Previous timer reading
        max_value: Maximum timer value before rollover
    
    Returns:
        Actual time difference accounting for rollover
    """
    if current_value < previous_value:
        # Rollover detected
        return (max_value - previous_value) + current_value
    else:
        return current_value - previous_value
```

## Performance Considerations

### Streaming Rate

Maximum sustainable edge detection rate depends on:

- **USB bandwidth**: ~1 MB/s for LabJack T4
- **CPU processing**: Modern CPUs easily handle required rates
- **Disk I/O**: CSV writing is buffered

**Typical limits:**
- Up to ~100,000 edges per second
- Limited by USB communication overhead
- File size grows ~40 bytes per edge

### Memory Usage

Memory usage is modest:

- **Streaming buffer**: ~1-10 MB
- **Processing overhead**: <100 MB
- **Output buffering**: Configurable

### File Size Estimation

```
File Size ≈ (Total Edges) × 60 bytes

Example:
- 2 clocks at 100 Hz for 60 seconds
- 2 × 100 Hz × 60 s × 2 edges/cycle = 24,000 edges
- File size ≈ 24,000 × 60 = 1.44 MB
```

Note: Each row contains three 64-bit integers plus delimiters and newline.

## Error Handling

### Common Issues

**Dropped samples:**
- Occurs if streaming can't keep up
- XClock logs warnings
- Check USB connection quality

**Disk full:**
- Writing stops gracefully
- Partial data saved
- Error message logged

**Device disconnection:**
- Streaming stops
- Exception raised
- Partial data may be recovered

## Advanced Usage

### Custom Processing Pipeline

```python
import numpy as np
from pathlib import Path

def process_edge_stream(filename, callback):
    """
    Process timestamp file with custom callback.
    
    Args:
        filename: Path to timestamp CSV
        callback: Function called for each edge (timestamp_ns, edge_type)
    """
    data = np.loadtxt(filename, dtype=np.int64, delimiter=",")
    for timestamp_ns, edge_type in data:
        callback(timestamp_ns, edge_type)

# Example: Real-time frequency measurement
class FrequencyMonitor:
    def __init__(self, clock_id):
        self.clock_id = clock_id
        self.last_time = None
        self.frequencies = []
    
    def process_edge(self, timestamp_ns, edge_type):
        # Only process rising edges of our clock
        if edge_type != self.clock_id:
            return
        
        if self.last_time is not None:
            interval_s = (timestamp_ns - self.last_time) / 1e9
            freq_hz = 1.0 / interval_s
            self.frequencies.append(freq_hz)
        
        self.last_time = timestamp_ns
    
    def get_stats(self):
        if not self.frequencies:
            return None
        return {
            'mean': np.mean(self.frequencies),
            'std': np.std(self.frequencies),
            'min': np.min(self.frequencies),
            'max': np.max(self.frequencies),
        }

# Use it
monitor = FrequencyMonitor(clock_id=1)
process_edge_stream("timestamps.csv", monitor.process_edge)
stats = monitor.get_stats()
print(f"Clock 1 frequency: {stats['mean']:.2f} ± {stats['std']:.2f} Hz")
```

## See Also

- {doc}`devices` - Device API reference
- {doc}`errors` - Error handling
- {doc}`../user/quickstart` - Usage examples
- {doc}`../developer/architecture` - System architecture