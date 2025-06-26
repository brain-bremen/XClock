# Example of using the LabJack T4 device to configure clock channels and start clocks in
# different manners. This example assumes you have the xclock library installed and a
# LabJack T4 device connected with the drivers installed.

from xclock.devices import LabJackT4
import time

# configure device
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

print(t4)

# start clock right here
t4.start_clocks()
time.sleep(3)
t4.stop_clocks()

# start clocks and wait until pulsed clocks are done
start_time = time.time()
t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)
elapsed = time.time() - start_time
print(f"start_clocks returned after {elapsed:.3f} seconds")


# wait for an input trigger to start clock
input_trigger_channel = t4.get_available_input_start_trigger_channels()[0]
timeout = 20  # s

print(
    f"Waiting for trigger edge on channel '{input_trigger_channel}' with a timeout {timeout} seconds..."
)
if t4.wait_for_trigger_edge(input_trigger_channel, timeout_s=timeout):
    print("Started clocks")
    t4.start_clocks()
    time.sleep(3)
    t4.stop_clocks
