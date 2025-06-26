# XClock - Tools for synchronizing eXperimental Clocks

XClock is a Python package designed to help synchronize data acquisition clocks in
experimental setups, particularly for neuroscience and behavioral experiments. It provides
tools to generate precise clock signals using various data acquisition (DAQ) devices, such
as the LabJack T4.

## Installation

...

## Get started

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
```
