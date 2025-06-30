import pytest
from xclock.errors import XClockException, XClockValueError
from xclock.devices import ClockDaqDevice

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
def test_start_clocks(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    # Add a clock channel
    clock_channel = device.add_clock_channel(
        100, available_clock_channels[0], None, False
    )

    # Start the clock
    device.start_clocks()

    # Check if the clock is running
    assert clock_channel.clock_enabled

    # Stop the clock
    device.stop_clocks()

    # Check if the clock is stopped
    assert not clock_channel.clock_enabled

    device.clear_clocks()


@pytest.mark.skipif(not hardware_available, reason="Labjack T4 not available")
def test_start_pulsed_clocks_and_wait(device: ClockDaqDevice):
    available_clock_channels = device.get_available_output_clock_channels()
    assert len(available_clock_channels) > 0

    device.clear_clocks()

    # Add a pulsed clock channel
    clock_channel = device.add_clock_channel(
        clock_tick_rate_hz=100,
        channel_name=available_clock_channels[0],
        number_of_pulses=10,
        enable_clock_now=False,
    )

    # Start the clock
    device.start_clocks(wait_for_pulsed_clocks_to_finish=True)

    # Check if the clock is stopped
    assert not clock_channel.clock_enabled

    device.clear_clocks()
