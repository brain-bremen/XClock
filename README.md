# XClock - Tools for synchronizing eXperimental Clocks

XClock is a Python package designed to help synchronize data acquisition clocks in
experimental setups, particularly for neuroscience and behavioral experiments. It provides
tools to generate precise clock signals using various data acquisition (DAQ) devices, such
as the [LabJack T4](https://labjack.com/products/labjack-t4). 

XClock allows you to output **multiple clock frequencies simultaneously**, all synchronized to
the same internal clock source to ensure precise timing alignment.

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
import time

t4 = LabJackT4()
available_clock_channels = t4.get_available_output_clock_channels()

t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=available_clock_channels[0],
    enable_clock_now=False,
    number_of_pulses=None,  # continuous output
)

t4.add_clock_channel(
    clock_tick_rate_hz=50,
    channel_name=available_clock_channels[1],
    enable_clock_now=False,
    number_of_pulses=5,  # pulsed output
)


# start clocks right here
t4.start_clocks()
time.sleep(3)
t4.stop_clocks()
```

See more examples in the [examples directory](examples/labjack_t4.py).