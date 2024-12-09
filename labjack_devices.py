from daq_device import ClockDaqDevice
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


class LabJackT4:
    """LabJack T4 device class

    Supports two clock signals on FIO6 and FIO7. The base clock
    frequency is 80 MHz.

    """

    available_clock_channels = ("DIO6", "DIO7")

    base_clock_frequency = 80_000_000  # 80 MHz
    divisor = 256

    handle: int

    _used_clock_channels: set[str] = set()
    _unused_clock_channels: set[str]

    def __init__(self):

        try:
            self.handle = ljm.openS("T4", "ANY", "ANY")
        except Exception as e:
            logger.error(f"Failed to open LabJack T4: {str(e)}")
            self.handle = None
            raise e

        (deviceType, connectionType, serialNumber, _, _, _) = ljm.getHandleInfo(
            self.handle
        )
        assert deviceType == ljm.constants.dtT4, "Device is not a LabJack T4"

        connectionTypeString = (
            "USB" if connectionType == ljm.constants.ctUSB else "Ethernet"
        )
        logger.debug(
            f"Opened LabJack T4 with serial number {serialNumber} via {connectionTypeString}"
        )

        # disable clock0 as its mutually exclusive with CLOCK1 and CLOCK2
        self._enable_clock(0, False)

        self._unused_clock_channels = set(LabJackT4.available_clock_channels)

    @check_if_initialized
    def start_continuous_clocks(self):

        # DIO_EF_CLOCK0_ENABLE
        # enable PWM: DIO#_EF_ENABLE
        # TODO: enable channels at the same time using eWriteNames
        for channel in self._used_clock_channels:
            registers = LabJackClockChannelRegisterNames(channel)
            ljm.eWriteName(self.handle, registers.enable, 1)

    @check_if_initialized
    def add_clock_channel(
        self,
        sample_rate: int,
        channel_name: str | None = None,
        enable_now: bool = True,
        # on_time=None,
        # off_time=None,
    ):

        if len(self._unused_clock_channels) == 0:
            raise ValueError(
                "No more clock channels available. Used channels: {self._used_clock_channels}"
            )

        # TODO: Check if sample rate is within limits
        # if sample_rate > self.base_clock_frequency//self.divisor:
        #     raise ValueError(
        #         f"Sample rate {sample_rate} exceeds base clock frequency {self.base_clock_frequency}"
        #     )

        if channel_name is None:
            channel_name = self._unused_clock_channels.pop()

        if channel_name not in LabJackT4.available_clock_channels:
            raise ValueError(
                "Invalid clock channel name {channel_name}. Must be in {LabJackT4.available_clock_channels}"
            )

        clock_id = (
            len(self._used_clock_channels) + 1
        )  # CLOCK1 and CLOCK2 are used for PWM
        roll_value = self.base_clock_frequency // self.divisor // sample_rate
        self._configure_clock(
            clock_id=clock_id,
            divisor=self.divisor,
            roll_value=roll_value,
            enable=enable_now,
        )

        self._configure_clock_channel(
            roll_value=roll_value,
            channel_name=channel_name,
            clock_id=clock_id,
            enable=enable_now,
        )

        self._used_clock_channels.add(channel_name)
        logger.debug(
            f"Added clock channel {channel_name} with sample rate {sample_rate}"
        )

    def _configure_clock_channel(
        self, roll_value: int, channel_name: str, clock_id: int, enable: bool = True
    ):

        registers = LabJackClockChannelRegisterNames(channel_name)

        duty_cycle = round(0.25 * roll_value)

        # disable, as we cannot change index if enabled
        ljm.eWriteName(self.handle, registers.enable, 0)

        # DIO_EF_CLOCK0_ENABLE = 0 // Disable the clock during config
        self._enable_clock(clock_id=clock_id, enable=False)

        # DIO#_EF_INDEX = 0 // PWM out index
        ljm.eWriteName(self.handle, registers.feature_index, PWM_OUT_FEATURE_INDEX)
        ljm.eWriteName(self.handle, registers.feature_config, duty_cycle)
        ljm.eWriteName(self.handle, registers.clock_source, clock_id)

        # re-enable clock if configured
        self._enable_clock(clock_id=clock_id, enable=enable)

    @check_if_initialized
    def disable_clock_channel(self, clock_channel: LabJackClockChannelRegisterNames):

        # disable clock: DIO_EF_CLOCK0_ENABLE
        self._enable_clock(False)

        # enable PWM: DIO#_EF_ENABLE
        ljm.eWriteName(self.handle, clock_channel.enable, 0)

    def __str__(self):
        return f"LabJack T4 with handle {self.handle}"

    def __del__(self):
        ljm.close(self.handle)

    def _enable_clock(self, clock_id: int = 0, enable: bool = True):
        ljm.eWriteName(self.handle, LabJackClockRegisters(clock_id).enable, int(enable))

    def _configure_clock(
        self, clock_id: int, divisor: int, roll_value: int, enable: bool = True
    ):

        register_names = LabJackClockRegisters(clock_id)

        # disable the clock during config
        ljm.eWriteName(self.handle, register_names.enable, 0)

        # configure the clock
        ljm.eWriteName(self.handle, register_names.divisor, divisor)
        ljm.eWriteName(self.handle, register_names.roll_value, roll_value)

        # set to configured state
        ljm.eWriteName(self.handle, register_names.enable, int(enable))


if __name__ == "__main__":

    logger.debug("Starting LabJack T4 device...")
    t4 = LabJackT4()
    t4.add_clock_channel(1000)
    t4.add_clock_channel(1000)
