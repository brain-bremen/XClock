from daq_device import DaqDevice
import labjack
import labjack.ljm as ljm
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PWM_OUT_FEATURE_INDEX = 0


# decorator to check if device is initialized
def check_if_initialized(func):
    def wrapper(*args, **kwargs):
        if args[0].handle is None:
            raise ValueError("LabJack T4 device is not initialized")
        return func(*args, **kwargs)

    return wrapper


@dataclass
class LabJackClockChannelRegisterNames:
    channel: str  # DIO#
    enable: str  # DIO#_EF_ENABLE
    feature_index: str  # DIO#_EF_INDEX
    feature_config: str  # DIO#_EF_CONFIG_A
    clock_source: str  # DIO#_EF_CLOCK_SOURCE

    def __init__(self, channel: str):
        self.channel = channel
        self.enable = f"{channel}_EF_ENABLE"
        self.feature_index = f"{channel}_EF_INDEX"
        self.feature_config = f"{channel}_EF_CONFIG_A"
        self.clock_source = f"{channel}_EF_CLOCK_SOURCE"


@dataclass
class LabJackClockRegisters:
    enable: str  # DIO_EF_CLOCK#_ENABLE
    roll_value: str  # DIO_EF_CLOCK#_ROLL_VALUE
    divisor: str  # DIO_EF_CLOCK#_DIVISOR

    def __init__(self, clock_source: int):
        self.enable = f"DIO_EF_CLOCK{clock_source}_ENABLE"
        self.roll_value = f"DIO_EF_CLOCK{clock_source}_ROLL_VALUE"
        self.divisor = f"DIO_EF_CLOCK{clock_source}_DIVISOR"


@dataclass
class ClockChannel:
    channel_name: str
    clock_source: int
    enabled: bool
    sample_rate: int


def _enable_clocks(handle: int, clock_ids: list[int] = [0], enable: bool = True):
    ljm.eWriteNames(
        handle,
        len(clock_ids),
        [LabJackClockRegisters(id).enable for id in clock_ids],
        [int(enable)] * len(clock_ids),
    )


def _configure_clock_channel(
    handle: int, roll_value: int, channel_name: str, clock_id: int, enable: bool = True
):
    registers = LabJackClockChannelRegisterNames(channel_name)

    duty_cycle = round(0.25 * roll_value)

    # disable, as we cannot change index if enabled
    ljm.eWriteName(handle, registers.enable, 0)

    # DIO_EF_CLOCK0_ENABLE = 0 // Disable the clock during config
    _enable_clocks(handle=handle, clock_ids=[clock_id], enable=False)

    # DIO#_EF_INDEX = 0 // PWM out index
    ljm.eWriteName(handle, registers.feature_index, PWM_OUT_FEATURE_INDEX)
    ljm.eWriteName(handle, registers.feature_config, duty_cycle)
    ljm.eWriteName(handle, registers.clock_source, clock_id)

    # re-enable clock if configured
    _enable_clocks(handle=handle, clock_ids=[clock_id], enable=enable)

    # enable channel if enalbe_now is True
    if enable:
        ljm.eWriteName(handle, registers.enable, 1)


def _configure_clock(
    handle, clock_id: int, divisor: int, roll_value: int, enable: bool = True
):
    register_names = LabJackClockRegisters(clock_id)

    # disable the clock during config
    ljm.eWriteName(handle, register_names.enable, 0)

    # configure the clock
    ljm.eWriteName(handle, register_names.divisor, divisor)
    ljm.eWriteName(handle, register_names.roll_value, roll_value)

    # set to configured state
    ljm.eWriteName(handle, register_names.enable, int(enable))


def _configure_input_trigger_channel(handle: int):
    pass


class LabJackT4:
    """LabJack T4 device class

    Supports two clock signals on FIO6/DIO6 and FIO7/DIO7. The base clock
    frequency is 80 MHz.

    """

    # TODO: timestamps of rising TTL pulses can be recorded from these (including self-generated)
    available_input_clock_channels = "DIO"

    # TODO: channels that can be used to trigger a recording
    available_input_start_trigger_channels = ("DIO11", "DIO12")

    # clock signals can be given out on these channels
    available_output_clock_channels = ("DIO6", "DIO7")

    base_clock_frequency = 80_000_000  # 80 MHz
    divisor = 256

    handle: int
    deviceType: int
    connectionType: int
    serialNumber: int

    _used_clock_channel_names: set[str] = set()
    _unused_clock_channel_names: set[str]
    _clock_channels: list[ClockChannel] = []

    def __init__(self):
        try:
            self.handle = ljm.openS("T4", "ANY", "ANY")
        except Exception as e:
            logger.error(f"Failed to open LabJack T4: {str(e)}")
            # self.handle = None
            raise e

        (self.deviceType, self.connectionType, self.serialNumber, _, _, _) = (
            ljm.getHandleInfo(self.handle)
        )
        assert self.deviceType == ljm.constants.dtT4, "Device is not a LabJack T4"

        connectionTypeString = (
            "USB" if self.connectionType == ljm.constants.ctUSB else "Ethernet"
        )
        logger.debug(
            f"Opened LabJack T4 with serial number {self.serialNumber} via {connectionTypeString}"
        )

        # disable clock0 as its mutually exclusive with CLOCK1 and CLOCK2
        _enable_clocks(self.handle, [0], False)

        self._unused_clock_channel_names = set(
            LabJackT4.available_output_clock_channels
        )

    @check_if_initialized
    def start_continuous_clocks(self):
        # Enable all clock channels at the same time using eWriteNames
        names = []
        values = []
        for channel in self._clock_channels:
            registers = LabJackClockChannelRegisterNames(channel.channel_name)
            names.append(registers.enable)
            values.append(1)
        if names:
            ljm.eWriteNames(self.handle, len(names), names, values)
        # Enable all clocks at the same time
        # for channel in self._clock_channels:
        _enable_clocks(
            handle=self.handle,
            clock_ids=[channel.clock_source for channel in self._clock_channels],
            enable=True,
        )

    def stop_continuous_clocks(self):
        pass

    def wait_for_trigger_to_start_clocks(self):
        pass

    @check_if_initialized
    def add_clock_channel(
        self,
        sample_rate_hz: int,
        channel_name: str | None = None,
        enable_now: bool = True,
        # on_time=None, TODO: Implement on_time and off_time via duty_cycle
        # off_time=None,
    ):
        if len(self._unused_clock_channel_names) == 0:
            raise ValueError(
                "No more clock channels available. Used channels: {self._used_clock_channels}"
            )

        # TODO: Check if sample rate is within limits
        # if sample_rate > self.base_clock_frequency//self.divisor:
        #     raise ValueError(
        #         f"Sample rate {sample_rate} exceeds base clock frequency {self.base_clock_frequency}"
        #     )

        if channel_name is None:
            channel_name = self._unused_clock_channel_names.pop()

        if channel_name not in LabJackT4.available_output_clock_channels:
            raise ValueError(
                "Invalid clock channel name {channel_name}. Must be in {LabJackT4.available_clock_channels}"
            )

        clock_id = (
            len(self._used_clock_channel_names) + 1
        )  # CLOCK1 and CLOCK2 are used for PWM
        roll_value = self.base_clock_frequency // self.divisor // sample_rate_hz
        _configure_clock(
            handle=self.handle,
            clock_id=clock_id,
            divisor=self.divisor,
            roll_value=roll_value,
            enable=enable_now,
        )
        actual_sample_rate = self.base_clock_frequency // self.divisor // roll_value

        _configure_clock_channel(
            handle=self.handle,
            roll_value=roll_value,
            channel_name=channel_name,
            clock_id=clock_id,
            enable=enable_now,
        )

        self._used_clock_channel_names.add(channel_name)
        logger.debug(
            f"Added clock channel {channel_name} with sample rate {sample_rate_hz}"
        )

        self._clock_channels.append(
            ClockChannel(
                channel_name=channel_name,
                clock_source=clock_id,
                enabled=enable_now,
                sample_rate=actual_sample_rate,
            )
        )

    def remove_clock_channel(self, channel_name: str):
        pass

    def __str__(self):
        out = f"LabJack T4 with handle {self.handle}:\n"
        for channel in self._clock_channels:
            out += f"\t- {str(channel)}\n"
        return out

    def __del__(self):
        ljm.close(self.handle)

    def wait_for_rising_edge(self, channel_name: str, timeout: float = 5.0) -> bool:
        """
        Waits for a rising edge (0->1) on the specified digital input channel.
        Returns True if a rising edge is detected within the timeout, else False.
        Uses LJM_WaitForNextInterval for precise polling.
        """
        import time

        interval_us = 1000  # 1 ms
        register = channel_name
        start_time = time.time()
        prev_value = ljm.eReadName(self.handle, register)
        interval_handle = 1  # Use 1 as the interval handle ID
        ljm.startInterval(interval_handle, interval_us)
        try:
            while time.time() - start_time < timeout:
                value = ljm.eReadName(self.handle, register)
                if prev_value == 0 and value == 1:
                    logger.debug(f"Rising edge detected on {channel_name}")
                    return True
                prev_value = value
                ljm.waitForNextInterval(interval_handle)
        finally:
            ljm.cleanInterval(interval_handle)
        logger.warning(f"Timeout waiting for rising edge on {channel_name}")
        return False


if __name__ == "__main__":
    logger.debug("Starting LabJack T4 device...")
    t4 = LabJackT4()
    available_clock_channels = t4.available_output_clock_channels

    t4.add_clock_channel(
        sample_rate_hz=40, channel_name=available_clock_channels[1], enable_now=False
    )

    t4.add_clock_channel(
        sample_rate_hz=20, channel_name=available_clock_channels[0], enable_now=False
    )

    print(t4)
    if t4.wait_for_rising_edge("DIO4", timeout=20):
        t4.start_continuous_clocks()
    else:
        logger.debug("Timeout after ")
