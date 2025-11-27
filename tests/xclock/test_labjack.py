import time

import numpy as np
import pytest

from xclock.devices import ClockDaqDevice
from xclock.devices.labjack_devices import LabJackEdgeStreamer, LabJackT4
from xclock.errors import XClockException, XClockValueError

DEVICE_NAME = "LabJack T4"
DEVICE_CLASS = LabJackT4

# Try to instantiate the hardware
try:
    daq_device = DEVICE_CLASS()
    hardware_available = True
except Exception as e:
    hardware_available = False


@pytest.fixture(scope="module")
def device():
    """Fixture to provide the device."""
    if not hardware_available:
        pytest.skip(f"{DEVICE_NAME} hardware not available")
    return daq_device


@pytest.fixture(autouse=True)
def run_before_and_after_tests(device):
    device.clear_clocks()


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_automatic_clock_channel_selection(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()

    clock_channels = []
    for channel in available_clock_channels:
        clock_channels.append(device.add_clock_channel(clock_tick_rate_hz=30))

    assert device.get_added_clock_channels() == clock_channels

    # should fail as there are no more channels
    with pytest.raises(XClockException):
        device.add_clock_channel(clock_tick_rate_hz=30)


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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
    assert loaded_data.shape == (number_of_pulses * 2, 3)
    # check that frequency is roughly in range
    dt = np.diff(loaded_data[loaded_data[:, 1] == 1, 0])
    assert np.all(np.abs(dt - expected_dt_ns) < tolerance_ns)


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
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
    daq_device.start_clocks(wait_for_pulsed_clocks_to_finish=True)

    streamer.stop_streaming()

    assert streamer.number_of_detected_edges == number_of_pulses * 2


def test_timer_rollover_detection():
    """Test CORE_TIMER rollover detection logic with synthetic data."""
    # Simulate the rollover detection logic from LabJackEdgeStreamer

    UINT32_MAX = 2**32
    ROLLOVER_THRESHOLD = -(2**31)

    # Test case 1: Normal incremental values (no rollover)
    last_timer = np.int64(1000000)
    current_batch = np.array([1000100, 1000200, 1000300], dtype=np.int64)

    timer_offset = np.int64(0)
    rollover_count = 0

    if last_timer > 0:
        timer_diff = current_batch - last_timer
        if current_batch[0] < last_timer and timer_diff[0] < ROLLOVER_THRESHOLD:
            rollover_count += 1
            timer_offset += np.int64(UINT32_MAX)

    current_batch += timer_offset

    assert rollover_count == 0, (
        "Should not detect rollover for normal incremental values"
    )
    assert timer_offset == 0, "Offset should remain 0"
    assert np.all(current_batch == [1000100, 1000200, 1000300])

    # Test case 2: Rollover occurs (timer wraps from near UINT32_MAX to 0)
    last_timer = np.int64(UINT32_MAX - 100)  # Close to rollover
    current_batch = np.array([50, 150, 250], dtype=np.int64)  # After rollover

    timer_offset = np.int64(0)
    rollover_count = 0

    if last_timer > 0:
        timer_diff = current_batch - last_timer
        if current_batch[0] < last_timer and timer_diff[0] < ROLLOVER_THRESHOLD:
            rollover_count += 1
            timer_offset += np.int64(UINT32_MAX)

    current_batch_corrected = current_batch + timer_offset

    assert rollover_count == 1, "Should detect rollover"
    assert timer_offset == UINT32_MAX, f"Offset should be 2^32, got {timer_offset}"
    # After correction, values should be monotonically increasing
    assert current_batch_corrected[0] > last_timer, (
        "First value should be greater than last after correction"
    )
    assert np.all(np.diff(current_batch_corrected) > 0), (
        "Values should be monotonically increasing"
    )

    # Test case 3: Multiple rollovers (second rollover)
    last_timer = current_batch_corrected[-1]  # Last value from previous batch
    current_batch = np.array([UINT32_MAX - 50, UINT32_MAX - 25, 10], dtype=np.int64)

    # First part of batch before second rollover
    timer_diff = current_batch - last_timer
    if current_batch[0] < last_timer and timer_diff[0] < ROLLOVER_THRESHOLD:
        rollover_count += 1
        timer_offset += np.int64(UINT32_MAX)

    current_batch_corrected = current_batch + timer_offset

    assert rollover_count == 2, "Should detect second rollover"
    assert timer_offset == 2 * UINT32_MAX, (
        f"Offset should be 2*2^32, got {timer_offset}"
    )
    assert current_batch_corrected[0] > last_timer, (
        "Values should continue increasing after second rollover"
    )

    # Test case 4: Edge case - small backward jump (should not trigger rollover)
    last_timer = np.int64(1000000)
    current_batch = np.array(
        [999999, 1000000, 1000001], dtype=np.int64
    )  # Small backward jump

    timer_offset = np.int64(0)
    rollover_count = 0

    if last_timer > 0:
        timer_diff = current_batch - last_timer
        if current_batch[0] < last_timer and timer_diff[0] < ROLLOVER_THRESHOLD:
            rollover_count += 1
            timer_offset += np.int64(UINT32_MAX)

    assert rollover_count == 0, "Should not detect rollover for small backward jump"
    assert timer_offset == 0, "Offset should remain 0 for small backward jump"

    print("All rollover detection tests passed!")


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_timer_rollover_in_streamer():
    """Test that LabJackEdgeStreamer correctly initializes rollover tracking variables."""
    if not hardware_available:
        pytest.skip(f"{DEVICE_NAME} hardware not available")

    channel_names = ["DIO6"]
    streamer = LabJackEdgeStreamer(
        daq_device.handle,
        channel_names,
        daq_device.base_clock_frequency_hz,
        scan_rate_hz=1000,
    )

    # Verify rollover tracking variables are initialized
    assert hasattr(streamer, "_timer_rollover_count"), (
        "Streamer should have _timer_rollover_count attribute"
    )
    assert hasattr(streamer, "_timer_offset"), (
        "Streamer should have _timer_offset attribute"
    )
    assert streamer._timer_rollover_count == 0, "Initial rollover count should be 0"
    assert streamer._timer_offset == 0, "Initial timer offset should be 0"

    print("Streamer rollover tracking initialization test passed!")
