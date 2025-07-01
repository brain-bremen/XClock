# XClock - Synchronizing eXperimental Clocks

![](resources/logo_with_clock_signals.png)


XClock is a Python package designed to help synchronize data acquisition clocks in
experimental setups, particularly for neuroscience and behavioral experiments. It provides
tools to generate precise clock signals using various data acquisition (DAQ) devices, such
as the [LabJack T4](https://labjack.com/products/labjack-t4). 

XClock allows you to 
- output **multiple clock frequencies simultaneously**, all synchronized to the same
  internal clock source to ensure precise timing alignment. 
- record the timestamps of the clock pulses relative to the internal DAQ device clock

The given output pulses can be used to trigger and synchronize industrial cameras used for
behavioral monitoring or two-photon imaging. 

*Note*: This Python project is not the [clock for the original X Window
System](https://www.x.org/archive/X11R7.6/doc/man/man1/xclock.1.xhtml).

[![Python Tests](https://github.com/brain-bremen/XClock/actions/workflows/python-tests.yml/badge.svg)](https://github.com/brain-bremen/XClock/actions/workflows/python-tests.yml)

## Installation

1. Install the software for you DAQ device, e.g. for the LabJack T Series from [here](https://support.labjack.com/docs/ljm-software-installer-downloads-t4-t7-t8-digit).


2. Install the `xclock` package. 
  ```bash
  # via pip
  pip install git+http://github.com/brain-bremen/XClock.git

  # via uv (recommended)
  uv add git+https://github.com/brain-bremen/XClock.git
  ```

3. Verify installation by running the CLI tool:
  ```bash
  xclock --help
  ```

## Use `xclock` library in your Python scripts

To use your DAQ device as a clock 


```python
from xclock.devices import LabJackT4
import pathlib
import numpy as np

t4 = LabJackT4()
available_clock_channels = t4.get_available_output_clock_channels()

# add two clocks with a defined number of clock pulses (~10 s)
t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=available_clock_channels[0],
    enable_clock_now=False,
    number_of_pulses=1000,
)

t4.add_clock_channel(
    clock_tick_rate_hz=60,
    channel_name=available_clock_channels[1],
    enable_clock_now=False,
    number_of_pulses=600, 
)

output_filename = pathlib.Path.home() / "Documents" / "XClock" / "foo.csv"
t4.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    filename=output_filename
)

# load and inspect data
loaded_data = np.loadtxt(output_filename, dtype=np.int64, delimiter=",")
```

See more examples in the [examples directory](examples/labjack_examples.py).

## Use `xclock` CLI tool for controlling clocks

The `xclock` CLI tool provides a convenient command-line interface to control clock
generation without writing Python scripts. It supports all the core functionality through
simple commands.

### Installation

After installing the XClock package, the `xclock` command becomes available in your terminal:

```bash
# Install the package first (see Installation section above)
uv add git+https://github.com/brain-bremen/XClock.git
xclock --help

# or directly run it using uvx / uv tool
uvx git+https://github.com/brain-bremen/XClock.git
```

### Basic Usage

The CLI uses a simple structure: global options followed by a command.

```bash
xclock [OPTIONS] COMMAND
```

### Available Commands

- `start` - Start clocks with specified rates
- `stop` - Stop all running clocks

### Common Options

- `--clock-tick-rates RATES` - Comma-separated clock frequencies in Hz (required for start)
- `--device DEVICE` - DAQ device to use (default: labjackt4)
- `--verbose, -v` - Enable detailed logging
- `--when {now,on_trigger}` - When to start clocks (default: now)
- `--duration SECONDS` - Run clocks for specified duration (0 = continuous)
- `--number-of-pulses PULSES` - Generate specific number of pulses per clock
- `--record-timestamps` - Save edge timestamps to CSV file
- `--timeout SECONDS` - Timeout when waiting for trigger

### Examples

```bash
# Start two continuous clocks at 60Hz and 100Hz for 10 seconds
xclock --clock-tick-rates 60,100 --duration 10 start

# Generate pulsed clocks: 200 pulses at 60Hz, 150 pulses at 100Hz
xclock --clock-tick-rates 60,100 --number-of-pulses 200,150 start

# Wait for external trigger before starting clocks
xclock --clock-tick-rates 60,100 --when on_trigger start

# Record edge timestamps while generating clocks
xclock --clock-tick-rates 60,100 --record-timestamps --number-of-pulses 100,150 start

# Stop any running clocks
xclock stop

# Start with verbose logging for debugging
xclock --clock-tick-rates 60,100 --verbose --duration 5 start
```

### Trigger Mode

When using `--when on_trigger`, the CLI will:
1. Configure the clocks but not start them
2. Wait for a rising edge on the device's trigger input (e.g. DIO4 for LabJack T4)
3. Start clocks immediately when a trigger is detected
4. Use `--timeout` to set maximum wait time (0 = no timeout)

### Timestamp Recording

When using `--record-timestamps`, the CLI will:
- Monitor clock outputs and record all edge transitions
- Save timestamps to `~/Documents/XClock/xclock_timestamps_<date>.csv`
- Format: `timestamp_ns, edge_type` (<0: falling edge, >0: rising edge, number is clock channel index)

## Device Support

Currently supported devices:
- `labjackt4` - LabJack T4 (default)

## Adding a different, unsupported device as a clock

Currently only the LabJack T4 is supported to be used as a clock device. Adding a new device
entails the following steps

- Write a class similar to `LabJackT4` that adheres to (inherits from) the interface defined
  in `ClockDaqDevice`. Implement all the abstract methods.
- For testing, copy `test_labjack.py` into a new file and adjust the `DEVICE_NAME` and
  `DEVICE_CLASS` variables. If your device class adheres to the interface, all tests should
  run and complete sucessfully.