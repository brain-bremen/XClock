# Command-Line Interface

The `xclock` command-line tool provides a convenient way to control clock generation without writing Python scripts. It supports all core functionality through simple commands.

## Installation

After installing the XClock package, the `xclock` command becomes available in your terminal:

```bash
# Verify installation
xclock --help

# Or run directly with uvx (no installation needed)
uvx git+https://github.com/brain-bremen/XClock.git --help
```

## Basic Usage

The CLI uses a simple structure: global options followed by a command.

```bash
xclock [OPTIONS] COMMAND
```

## Commands

### `start`

Start clocks with specified rates and configuration.

```bash
xclock --clock-tick-rates RATES start
```

**Example:**

```bash
xclock --clock-tick-rates 60,100 start
```

### `stop`

Stop all running clocks on the device.

```bash
xclock stop
```

## Global Options

These options apply to all commands and must be specified **before** the command.

### `--clock-tick-rates RATES`

**Required for start command**

Comma-separated list of clock frequencies in Hz.

```bash
xclock --clock-tick-rates 60,100,120 start
```

### `--device DEVICE`

Select which DAQ device to use.

- **Default**: `labjackt4`
- **Choices**: `labjackt4`, `dummydaqdevice`

```bash
xclock --device labjackt4 --clock-tick-rates 100 start
```

### `--duration SECONDS`

Run clocks for a specific duration in seconds. Auto-calculates the number of pulses for each clock based on its frequency.

- **Default**: `0` (continuous)
- **Mutually exclusive with**: `--number-of-pulses`

```bash
# Run for 30 seconds
xclock --clock-tick-rates 60,100 --duration 30 start
```

### `--number-of-pulses PULSES`

Comma-separated number of pulses for each clock.

- **Mutually exclusive with**: `--duration`

```bash
# Generate exactly 200 pulses on first clock, 150 on second
xclock --clock-tick-rates 60,100 --number-of-pulses 200,150 start
```

### `--when {now,on_trigger}`

When to start the clocks.

- **`now`** (default): Start immediately
- **`on_trigger`**: Wait for external trigger signal

```bash
xclock --clock-tick-rates 100 --when on_trigger start
```

### `--timeout SECONDS`

Timeout in seconds when waiting for trigger. Only applicable when `--when on_trigger` is used.

- **Default**: `0` (no timeout)
- **Values**: `> 0` for timeout, `<= 0` for infinite wait

```bash
xclock --clock-tick-rates 100 --when on_trigger --timeout 60 start
```

### `--record-timestamps`

Record edge timestamps to a CSV file in `~/Documents/XClock/`.

```bash
xclock --clock-tick-rates 60,100 --record-timestamps start
```

Output file format: `xclock_timestamps_YYYY-MM-DD_HH-MM-SS.csv`

### `--detect-edges-on CHANNELS`

Comma-separated list of additional channels to monitor for edge detection (beyond the clock output channels).

```bash
xclock --clock-tick-rates 60,100 --record-timestamps --detect-edges-on EIO4,EIO5 start
```

### `--verbose` / `-v`

Enable verbose logging for debugging.

```bash
xclock --verbose --clock-tick-rates 100 start
```

## Examples

### Example 1: Simple Clock

Generate a 100 Hz clock for 10 seconds:

```bash
xclock --clock-tick-rates 100 --duration 10 start
```

### Example 2: Multiple Synchronized Clocks

Generate two synchronized clocks at different frequencies for 5 seconds:

```bash
xclock --clock-tick-rates 60,100 --duration 5 start
```

### Example 3: Exact Pulse Count

Generate exactly 500 pulses at 60 Hz and 800 pulses at 100 Hz:

```bash
xclock --clock-tick-rates 60,100 --number-of-pulses 500,800 start
```

### Example 4: Continuous Clock with Manual Stop

Start a continuous 100 Hz clock, then stop it manually:

```bash
# Terminal 1: Start continuous clock
xclock --clock-tick-rates 100 start

# Press Ctrl+C to stop, or...

# Terminal 2: Stop from another terminal
xclock stop
```

### Example 5: Trigger-Based Start

Wait for an external trigger before starting clocks:

```bash
xclock --clock-tick-rates 60,100 --when on_trigger --timeout 30 start
```

This will:
1. Configure the clocks but not start them
2. Wait for a rising edge on the trigger input (e.g., DIO4 on LabJack T4)
3. Start clocks immediately when trigger is detected
4. Timeout after 30 seconds if no trigger received

### Example 6: Record Timestamps

Generate clocks and record all edge timestamps:

```bash
xclock --clock-tick-rates 60,100 --duration 10 --record-timestamps start
```

Timestamps are saved to `~/Documents/XClock/xclock_timestamps_<timestamp>.csv`

### Example 7: Monitor Additional Channels

Record timestamps from clocks and additional input channels:

```bash
xclock --clock-tick-rates 60,100 --record-timestamps --detect-edges-on EIO4,EIO5 start
```

### Example 8: Verbose Debugging

Run with detailed logging for troubleshooting:

```bash
xclock --verbose --clock-tick-rates 100 --duration 5 start
```

### Example 9: Camera Synchronization

Synchronize two cameras at different frame rates for 5 minutes:

```bash
xclock --clock-tick-rates 30,60 --duration 300 --record-timestamps start
```

This creates:
- Clock 1: 30 Hz (9,000 pulses over 5 minutes)
- Clock 2: 60 Hz (18,000 pulses over 5 minutes)
- Timestamp file with all frame times

## Understanding Output

### Normal Output

```
2024-01-15 10:30:00 - cli.main - INFO - Added clock: 60 Hz on FIO0 (600 pulses, ~10s)
2024-01-15 10:30:00 - cli.main - INFO - Added clock: 100 Hz on FIO1 (1000 pulses, ~10s)
2024-01-15 10:30:00 - cli.main - INFO - Starting clocks...
2024-01-15 10:30:10 - cli.main - INFO - All pulsed clocks finished.
```

### Verbose Output

With `--verbose`, you get detailed debug information:

```
2024-01-15 10:30:00 - cli.main - DEBUG - Initializing LabJackT4 device
2024-01-15 10:30:00 - xclock.devices.labjack_devices - DEBUG - Opening LabJack T4 device
2024-01-15 10:30:00 - xclock.devices.labjack_devices - DEBUG - Device handle: 1
2024-01-15 10:30:00 - cli.main - INFO - Added clock: 60 Hz on FIO0 (600 pulses, ~10s)
...
```

### Trigger Wait Output

```
2024-01-15 10:30:00 - cli.main - INFO - Waiting for trigger on DIO4...
2024-01-15 10:30:00 - cli.main - INFO - Send a rising edge to start clocks. Press Ctrl+C to cancel.
2024-01-15 10:30:05 - cli.main - INFO - Trigger received! Starting clocks...
```

### Timestamp File Format

When using `--record-timestamps`, the output CSV file contains:

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Timestamp (nanoseconds) | Edge type | Unix timestamp (nanoseconds) |

**Column descriptions:**
- Column 1: Device-relative timestamp in nanoseconds (time since device start)
- Column 2: Edge type encoding
  - Positive integer (1, 2, 3, ...): Rising edge on clock 1, 2, 3, ...
  - Negative integer (-1, -2, -3, ...): Falling edge on clock 1, 2, 3, ...
  - Additional channels numbered sequentially after clocks
- Column 3: Unix timestamp in nanoseconds (host system time)

**Example CSV content:**

```csv
1000000,1,1638360000000000000
1500000,-1,1638360000500000000
2000000,1,1638360001000000000
2000000,2,1638360001000000000
2500000,-1,1638360001500000000
2500000,-2,1638360001500000000
```

The Unix timestamp (column 3) provides absolute wall-clock time for synchronization with other systems.

## Error Handling

### Common Errors

**Missing clock-tick-rates:**

```
Error: --clock-tick-rates is required for the start command
```

**Solution**: Add `--clock-tick-rates` option

**Device not found:**

```
Error: Failed to initialize labjackt4: Device not found
```

**Solutions**:
- Check USB connection
- Verify device drivers are installed
- Try reconnecting the device

**Mutually exclusive options:**

```
Error: duration and number-of-pulses are mutually exclusive. Provide only one.
```

**Solution**: Use either `--duration` or `--number-of-pulses`, not both

**Trigger timeout:**

```
INFO - Timeout waiting for trigger.
```

**Solutions**:
- Increase timeout value
- Check trigger signal connections
- Verify trigger signal levels



## See Also

- {doc}`quickstart` - Basic usage patterns
- {doc}`devices` - Device-specific information
- {doc}`../api/devices` - Python API reference