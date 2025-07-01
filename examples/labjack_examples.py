# Example of using the LabJack T4 device to configure clock channels and start clocks in
# different manners. This example assumes you have the xclock library installed and a
# LabJack T4 device connected with the drivers installed.

import pathlib
import time

import numpy as np

from xclock.devices import LabJackT4

# %% configure device for continuous clock output
t4 = LabJackT4()
available_clock_channels = t4.get_available_output_clock_channels()

t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=available_clock_channels[0],
    enable_clock_now=False,
    number_of_pulses=None,  # continuous output
)


print(t4)

# start clock right here
t4.start_clocks()
time.sleep(3)
t4.stop_clocks()
t4.clear_clocks()  # removes all clocks

# %% configure two clocks with different tick rates and a defined numer of pulses (~10 s)
# add two clocks with a defined number of clock pulses (~10 s)
clock1 = t4.add_clock_channel(
    clock_tick_rate_hz=100,
    channel_name=available_clock_channels[0],
    enable_clock_now=False,
    number_of_pulses=1000,
)

clock2 = t4.add_clock_channel(
    clock_tick_rate_hz=60,
    channel_name=available_clock_channels[1],
    enable_clock_now=False,
    number_of_pulses=600,
)

output_filename = pathlib.Path.home() / "Documents" / "XClock" / "foo.csv"

t4.start_clocks_and_record_edge_timestamps(
    wait_for_pulsed_clocks_to_finish=True, filename=output_filename
)

# load csv file containing the timestamps of the edges in nanoseconds for the two
# clocks
loaded_data = np.loadtxt(output_filename, dtype=np.int64, delimiter=",")

# check the number of pulses
print(
    f"Clock 1: {np.sum(loaded_data[:, 1] == 1)} rising edges, "
    f"{np.sum(loaded_data[:, 1] == -1)} falling edges"
)
print(
    f"Clock 2: {np.sum(loaded_data[:, 1] == 2)} rising edges, "
    f"{np.sum(loaded_data[:, 1] == -2)} falling edges"
)
# check frequency of clock 1
expected_dt_ns = int(1e9 / (clock1.actual_sample_rate_hz))
dt = np.diff(loaded_data[loaded_data[:, 1] == 1, 0])
tolerance_ns = 1000  # 1 microsecond
if np.all(np.abs(dt - expected_dt_ns) < tolerance_ns):
    print(
        f"All detected timestamps are within {tolerance_ns / 1000} microsecond deviation"
    )
