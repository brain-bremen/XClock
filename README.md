# XClock - Tools for synchronizing eXperimental Clocks

![](resources/logo_with_clock_signals.png)


XClock is a Python package designed to help synchronize data acquisition clocks in
experimental setups, particularly for neuroscience and behavioral experiments. It provides
tools to generate precise clock signals using various data acquisition (DAQ) devices, such
as the [LabJack T4](https://labjack.com/products/labjack-t4). 

XClock allows you to 
- output **multiple clock frequencies simultaneously**, all synchronized to the same
  internal clock source to ensure precise timing alignment. 
- record 

*Note*: This is not the [clock for the original X Window System](https://www.x.org/archive/X11R7.6/doc/man/man1/xclock.1.xhtml).



## Installation

1. Install the software for you DAQ device, e.g. for the LabJack T Series from [here](https://support.labjack.com/docs/ljm-software-installer-downloads-t4-t7-t8-digit).


2. Install the `xclock` package. 
  ```bash
  # via pip
  pip install git+http://github.com/brain-bremen/XClock.git

  # via uv (recommended)
  uv add git+https://github.com/brain-bremen/XClock.git

```

## Get started

To use your DAQ device as a clock 


```python
from xclock.devices import LabJackT4
import pathlib

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
device.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True,
    filename=output_filename
)

loaded_data = np.loadtxt(output_filename, dtype=np.int64, delimiter=",")
```

See more examples in the [examples directory](examples/labjack_t4.py).

## `xclock` CLI tool

The `xclock` CLI tool can be used to start clocks on a DAQ device as above, but directly
from the command line interface without writing your own Python script.

```bash
xclock --clock-tick-rates 60,100 --device labjack --duration 100 --verbose start
xclock --clock-tick-rates 60,100 --device labjack --number-of-pulses 200,150 start
xclock --clock-tick-rates= 60,100 --device labjack wait-for-trigger


```

## Adding a different, unsupported device as a clock

Currently only the LabJack T4 is supported to be used as a clock device. Adding a new device
entails the following steps

- Write a class similar to `LabJackT4` that adheres to (inherits from) the interface defined
  in `ClockDaqDevice`. Implement all the abstract methods.
- For testing, copy `test_labjack.py` into a new file and adjust the `DEVICE_NAME` and
  `DEVICE_CLASS` variables. If your device class adheres to the interface, all tests should
  run and complete sucessfully.