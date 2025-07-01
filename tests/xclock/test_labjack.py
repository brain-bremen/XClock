import pytest
import time
from xclock.errors import XClockException, XClockValueError
from xclock.devices import ClockDaqDevice
from xclock.devices.labjack_devices import LabJackEdgeStreamer
import numpy as np

# Try to instantiate the hardware
try:
    from xclock.devices import LabJackT4

    t4 = LabJackT4()
    hardware_available = True
except Exception as e:
    hardware_available = False


@pytest.fixture(scope="module")
def device():
    """Fixture to provide the LabJack T4 device."""
    if not hardware_available:
        pytest.skip("LabJack T4 hardware not available")
    return t4


@pytest.fixture(autouse=True)
def run_before_and_after_tests(device):
    device.clear_clocks()


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_add_clock_channel(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()

    assert len(available_clock_channels) > 0
    clock_channel = device.add_clock_channel(
        100, available_clock_channels[0], None, False
    )
    assert clock_channel.actual_sample_rate_hz == 100
    assert clock_channel.channel_name == available_clock_channels[0]
    assert not clock_channel.clock_enabled
    assert clock_channel.number_of_pulses is None

    # nonexistant channel must fail
    with pytest.raises(XClockException):
        device.add_clock_channel(100, "NONEXISTANT_CHANNEL", None, False)

    for channel in available_clock_channels[1:]:
        device.add_clock_channel(
            clock_tick_rate_hz=100,
            channel_name=channel,
            number_of_pulses=None,
            enable_clock_now=False,
        )

    assert [
        channel.channel_name for channel in device.get_added_clock_channels()
    ] == list(available_clock_channels)
    assert len(device.get_unused_clock_channel_names()) == 0

    device.clear_clocks()

    assert len(device.get_added_clock_channels()) == 0


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_start_and_stop_clocks(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    # Add a clock channel
    clock_channel = device.add_clock_channel(
        100, available_clock_channels[0], number_of_pulses=None, enable_clock_now=False
    )

    # Start the clock
    device.start_clocks(wait_for_pulsed_clocks_to_finish=False, timeout_duration_s=-1)

    # Check if the clock is running
    assert clock_channel.clock_enabled

    # Stop the clock
    device.stop_clocks()

    # Check if the clock is stopped
    assert not clock_channel.clock_enabled


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_automatic_clock_channel_selection(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()

    clock_channels = []
    for channel in available_clock_channels:
        clock_channels.append(device.add_clock_channel(clock_tick_rate_hz=30))

    assert device.get_added_clock_channels() == clock_channels

    # should fail as there are no more channels
    with pytest.raises(XClockException):
        device.add_clock_channel(clock_tick_rate_hz=30)


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_start_clocks_with_duration(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()

    clock_channels = []
    for channel in available_clock_channels:
        clock_channels.append(device.add_clock_channel(clock_tick_rate_hz=30))

    expected_duration = 1.0
    t_start = time.time()
    device.start_clocks(
        wait_for_pulsed_clocks_to_finish=False, timeout_duration_s=expected_duration
    )
    duration = time.time() - t_start
    assert duration > 0.95 * expected_duration and duration < 1.1 * expected_duration

    device.stop_clocks()

    with pytest.raises(XClockValueError):
        device.start_clocks(
            wait_for_pulsed_clocks_to_finish=True, timeout_duration_s=1.0
        )


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_start_pulsed_clocks_and_wait_for_finish(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    device.clear_clocks()

    # Add a pulsed clock channel
    clock_channel = device.add_clock_channel(
        clock_tick_rate_hz=100,
        channel_name=available_clock_channels[0],
        number_of_pulses=100,
        enable_clock_now=False,
    )

    # Start the clock
    t_start = time.time()
    device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
    duration = time.time() - t_start
    assert duration >= 0.99

    # Check if the clock is stopped
    assert not clock_channel.clock_enabled

    device.clear_clocks()


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_streaming(device: ClockDaqDevice, tmp_path):
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0
    device.clear_clocks()

    number_of_pulses = 500
    clock_tick_rate_hz = 100
    expected_dt_ns = int(1e9 / (clock_tick_rate_hz))
    tolerance_ns = 1000  # 1 microsecond
    # Add a pulsed clock channel
    clock_channel = device.add_clock_channel(
        clock_tick_rate_hz=clock_tick_rate_hz,
        channel_name=available_clock_channels[0],
        number_of_pulses=number_of_pulses,
        enable_clock_now=False,
    )
    device.start_clocks_and_record_edge_timestamps(
        timeout_duration_s=0,
        wait_for_pulsed_clocks_to_finish=True,
        filename=tmp_path / "foo.csv",
    )

    loaded_data = np.loadtxt(tmp_path / "foo.csv", dtype=np.int64, delimiter=",")
    assert loaded_data.shape == (number_of_pulses * 2, 2)
    # check that frequency is roughly in range
    dt = np.diff(loaded_data[loaded_data[:, 1] == 1, 0])
    assert np.all(np.abs(dt - expected_dt_ns) < tolerance_ns)


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_streaming_no_clocks(device: ClockDaqDevice):
    channel_names = ["DIO6"]
    streamer = LabJackEdgeStreamer(
        device.handle,
        channel_names,
        device.base_clock_frequency_hz,
        scan_rate_hz=1000,
    )

    streamer.start_streaming()
    assert streamer.is_streaming()
    import time

    time.sleep(1)
    streamer.stop_streaming()
    assert not streamer.is_streaming()


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_streaming_with_separate_streamer(device: ClockDaqDevice):
    # Setup LabJack

    number_of_pulses = 6
    device.add_clock_channel(100, "DIO6", number_of_pulses=number_of_pulses)

    channel_names = ["EIO6"]
    streamer = LabJackEdgeStreamer(
        device.handle, channel_names, device.base_clock_frequency_hz, scan_rate_hz=1000
    )

    streamer.start_streaming()
    assert streamer.is_streaming()
    t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)

    streamer.stop_streaming()

    assert streamer.number_of_detected_edges == number_of_pulses * 2
