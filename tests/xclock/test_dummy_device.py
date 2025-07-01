"""
Tests for DummyDaqDevice implementation.

This demonstrates how to test a device implementation.
"""

import pytest
import time
from xclock.errors import XClockException
from xclock.devices import ClockDaqDevice
from xclock.devices.dummy_daq_device import DummyDaqDevice

DEVICE_NAME = "Dummy Device"
DEVICE_CLASS = DummyDaqDevice

# Try to instantiate the hardware (dummy device should always work)
try:
    daq_device = DEVICE_CLASS()
    hardware_available = True
except Exception:
    hardware_available = False


@pytest.fixture(scope="module")
def device():
    """Fixture to provide the device."""
    if not hardware_available:
        pytest.skip(f"{DEVICE_NAME} hardware not available")
    return daq_device


@pytest.fixture(autouse=True)
def run_before_and_after_tests(device):
    """Clean up device state before and after each test."""
    device.clear_clocks()


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_add_clock_channel(device: ClockDaqDevice):
    """Test adding clock channels to the device."""
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
    with pytest.raises((XClockException, ValueError)):
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
    """Test starting and stopping clocks."""
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    # Add a clock channel
    clock_channel = device.add_clock_channel(
        100, available_clock_channels[0], number_of_pulses=None, enable_clock_now=False
    )

    # Start the clock
    device.start_clocks(wait_for_pulsed_clocks_to_finish=False, timeout_duration_s=0)

    # Check if the clock is running
    assert clock_channel.clock_enabled

    # Stop the clock
    device.stop_clocks()

    # Check if the clock is stopped
    assert not clock_channel.clock_enabled


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_automatic_clock_channel_selection(device: ClockDaqDevice):
    """Test automatic channel selection when no channel is specified."""
    available_clock_channels = device.get_available_output_clock_channels()

    clock_channels = []
    for channel in available_clock_channels:
        clock_channels.append(device.add_clock_channel(clock_tick_rate_hz=30))

    assert device.get_added_clock_channels() == clock_channels

    # should fail as there are no more channels
    with pytest.raises((XClockException, RuntimeError)):
        device.add_clock_channel(100)


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_start_clocks_with_duration(device: ClockDaqDevice):
    """Test starting clocks with a timeout duration."""
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    # Add a clock channel
    clock_channel = device.add_clock_channel(
        100, available_clock_channels[0], number_of_pulses=None, enable_clock_now=False
    )

    # Start the clock with a short duration
    start_time = time.time()
    device.start_clocks(wait_for_pulsed_clocks_to_finish=False, timeout_duration_s=0.1)
    elapsed_time = time.time() - start_time

    # Should return quickly since we're not waiting
    assert elapsed_time < 0.5
    assert clock_channel.clock_enabled


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_start_pulsed_clocks_and_wait_for_finish(device: ClockDaqDevice):
    """Test starting pulsed clocks and waiting for them to finish."""
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    number_of_pulses = 10
    sample_rate_hz = 100

    # Add a pulsed clock channel
    clock_channel = device.add_clock_channel(
        sample_rate_hz,
        available_clock_channels[0],
        number_of_pulses=number_of_pulses,
        enable_clock_now=False,
    )

    # Start the clock and wait for it to finish
    start_time = time.time()
    device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
    elapsed_time = time.time() - start_time

    # Should have waited for the pulses to complete
    expected_duration = number_of_pulses / sample_rate_hz
    assert elapsed_time >= expected_duration * 0.8  # Allow some tolerance

    # Pulsed clock should be disabled after finishing
    assert not clock_channel.clock_enabled


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_streaming(device: ClockDaqDevice, tmp_path):
    """Test timestamp recording functionality."""
    # Add a clock channel
    device.add_clock_channel(1000, "FOOCLK1", number_of_pulses=10)

    # Record timestamps to a temporary file
    timestamp_file = tmp_path / "test_timestamps.csv"
    device.start_clocks_and_record_edge_timestamps(
        wait_for_pulsed_clocks_to_finish=True, filename=timestamp_file
    )

    # Check that file was created and has content
    assert timestamp_file.exists()
    content = timestamp_file.read_text()
    assert "timestamp,channel,edge_type" in content
    assert "FOOCLK1" in content
    assert "rising" in content or "falling" in content


# Dummy device specific tests
@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_dummy_device_initialization(device: ClockDaqDevice):
    """Test that the dummy device initializes correctly."""
    assert device.handle == 0
    assert device.base_clock_frequency_hz == 80000000
    assert len(device.get_added_clock_channels()) == 0
    assert len(device.get_unused_clock_channel_names()) == 2


@pytest.mark.skipif(not hardware_available, reason=f"{DEVICE_NAME} not available")
def test_dummy_device_available_channels(device: ClockDaqDevice):
    """Test that the dummy device has the expected available channels."""
    input_channels = device.get_available_input_start_trigger_channels()
    output_channels = device.get_available_output_clock_channels()

    assert input_channels == ("FOOIO4", "FOOIO5")
    assert output_channels == ("FOOCLK1", "FOOCLK2")
