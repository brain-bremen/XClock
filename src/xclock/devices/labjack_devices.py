from enum import IntEnum
from xclock.devices.daq_device import DaqDevice, EdgeType
import labjack.ljm as ljm
import logging
from dataclasses import dataclass
from xclock.errors import XClockException

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ExtendedFeatureIndices(IntEnum):
    PWM_OUT_FEATURE_INDEX = 0
    PWM_OUT_WITH_PHASE_EF_INDEX = 1
    PULSE_OUT_EF_INDEX = 2


class DigIoRegisters:
    channel: str  # DIO#

    def __init__(self, channel: str):
        self.channel = channel

    @property
    def enable(self) -> str:
        return f"{self.channel}_EF_ENABLE"

    @property
    def feature_index(self) -> str:
        return f"{self.channel}_EF_INDEX"

    @property
    def feature_configA(self) -> str:
        return f"{self.channel}_EF_CONFIG_A"

    @property
    def feature_configB(self) -> str:
        return f"{self.channel}_EF_CONFIG_B"

    @property
    def feature_configC(self) -> str:
        return f"{self.channel}_EF_CONFIG_C"

    @property
    def clock_source(self) -> str:
        return f"{self.channel}_EF_CLOCK_SOURCE"


class ClockRegisters:
    clock_id: int

    def __init__(self, clock_id: int):
        self.clock_id = clock_id

    @property
    def enable(self):
        return f"DIO_EF_CLOCK{self.clock_id}_ENABLE"

    @property
    def roll_value(self):
        return f"DIO_EF_CLOCK{self.clock_id}_ROLL_VALUE"

    @property
    def divisor(self):
        return f"DIO_EF_CLOCK{self.clock_id}_DIVISOR"

    @property
    def options(self):
        return f"DIO_EF_CLOCK{self.clock_id}_OPTIONS"


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
        [ClockRegisters(id).enable for id in clock_ids],
        [int(enable)] * len(clock_ids),
    )


def _configure_pulsed_clock_channel(
    handle: int,
    number_of_pulses: int,
    roll_value: int,
    channel_name: str,
    clock_id: int,
    enable: bool = True,
):
    registers = DigIoRegisters(channel_name)

    duty_cycle = round(0.25 * roll_value)

    # disable, as we cannot change index if enabled
    ljm.eWriteName(handle, registers.enable, 0)

    # DIO_EF_CLOCK0_ENABLE = 0 // Disable the clock during config
    _enable_clocks(handle=handle, clock_ids=[clock_id], enable=False)

    config = {
        registers.clock_source: clock_id,
        registers.feature_index: ExtendedFeatureIndices.PULSE_OUT_EF_INDEX,
        registers.feature_configA: duty_cycle,
        registers.feature_configB: 0,
        registers.feature_configC: number_of_pulses,
    }

    if enable:
        config[registers.enable] = 1

    ljm.eWriteNames(
        handle=handle,
        numFrames=len(config),
        aNames=config.keys(),
        aValues=config.values(),
    )


def _configure_continuous_clock_channel(
    handle: int, roll_value: int, channel_name: str, clock_id: int, enable: bool = True
):
    """
    Configures a digital output channel to act as a continuous clock channel (PWM).

    Args:

        handle (int): The LJM handle for the LabJack device.
        roll_value (int): The roll value for the clock.
        channel_name (str): The name of the channel to configure (e.g., "DIO6").
        clock_id (int): The clock ID to use for the channel (1 or 2).
        enable (bool): Whether to enable the channel after configuration.

    """
    registers = DigIoRegisters(channel_name)

    duty_cycle = round(0.25 * roll_value)

    # disable, as we cannot change index if enabled
    ljm.eWriteName(handle, registers.enable, 0)

    # DIO_EF_CLOCK0_ENABLE = 0 // Disable the clock during config
    _enable_clocks(handle=handle, clock_ids=[clock_id], enable=False)

    config = {
        registers.feature_index: ExtendedFeatureIndices.PWM_OUT_FEATURE_INDEX,
        registers.clock_source: clock_id,
        registers.feature_configA: duty_cycle,
        registers.feature_configB: 0,
        registers.feature_configC: 0,
    }

    ljm.eWriteNames(
        handle=handle,
        numFrames=len(config),
        aNames=config.keys(),
        aValues=config.values(),
    )

    # re-enable clock if configured
    _enable_clocks(handle=handle, clock_ids=[clock_id], enable=enable)

    # enable channel if enalbe_now is True
    if enable:
        ljm.eWriteName(handle, registers.enable, 1)


def _configure_clock(
    handle, clock_id: int, divisor: int, roll_value: int, enable: bool = True
):
    register_names = ClockRegisters(clock_id)

    # disable the clock during config
    ljm.eWriteName(handle, register_names.enable, 0)

    # configure the clock
    clock_config = {
        register_names.divisor: divisor,
        register_names.roll_value: roll_value,
    }

    if enable:
        clock_config[register_names.enable] = int(enable)
    # set to configured state
    ljm.eWriteName(handle, register_names.enable, int(enable))
    ljm.eWriteNames(
        handle=handle,
        numFrames=len(clock_config),
        aNames=clock_config.keys(),
        aValues=clock_config.values(),
    )


def _configure_input_trigger_channel(handle: int):
    pass


class LabJackT4(DaqDevice):
    """LabJack T4 device class

    Supports two clock signals on FIO6/DIO6 and FIO7/DIO7. The base clock
    frequency is 80 MHz.

    """

    # clock signals can be given out on these channels
    available_output_clock_channels = ("DIO6", "DIO7")

    @staticmethod
    def get_available_output_clock_channels():
        return LabJackT4.available_output_clock_channels

    # the device can wait for triggers on these channels
    availabile_input_trigger_channels = ("DIO4", "DIO5")

    @staticmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        return LabJackT4.availabile_input_trigger_channels

    base_clock_frequency = 80_000_000  # 80 MHz
    divisor = 256

    handle: int | None = None
    deviceType: int
    connectionType: int
    serialNumber: int

    _used_clock_channel_names: set[str] = set()
    _unused_clock_channel_names: set[str]
    _clock_channels: list[ClockChannel] = []

    def __init__(self):
        # if not hasattr(ljm, "_staticLib"):
        #     raise XClockException(
        #         "Labjack library is not loaded. Have you installed it?"
        #     )

        try:
            self.handle = ljm.openS("T4", "ANY", "ANY")
        except Exception as e:
            self.handle = None
            logger.error(f"Failed to open LabJack T4: {str(e)}")
            exit()

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

    def start_continuous_clocks(self):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")
        # Enable all clocks at the same time
        _enable_clocks(
            handle=self.handle,
            clock_ids=[channel.clock_source for channel in self._clock_channels],
            enable=True,
        )

        # enable channels
        values = []
        names = []
        for channel in self._clock_channels:
            registers = DigIoRegisters(channel.channel_name)
            names.append(registers.enable)
            values.append(1)
        if names:
            ljm.eWriteNames(self.handle, len(names), names, values)
        # # Enable all clocks at the same time
        # _enable_clocks(
        #     handle=self.handle,
        #     clock_ids=[channel.clock_source for channel in self._clock_channels],
        #     enable=True,
        # )

    def stop_continuous_clocks(self):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")
        _enable_clocks(
            handle=self.handle,
            clock_ids=[channel.clock_source for channel in self._clock_channels],
            enable=False,
        )

    def add_continuous_clock_channel(
        self,
        sample_rate_hz: int,
        channel_name: str | None = None,
        enable_now: bool = True,
        # on_time=None, TODO: Implement on_time and off_time via duty_cycle
        # off_time=None,
    ):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")
        if len(self._unused_clock_channel_names) == 0:
            raise XClockException(
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
            raise XClockException(
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

        _configure_continuous_clock_channel(
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
        if self.handle:
            ljm.close(self.handle)

    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        """
        Waits for a rising edge (0->1) on the specified digital input channel.
        Returns True if a rising edge is detected within the timeout, else False.
        Uses LJM_WaitForNextInterval for precise polling.
        """
        import time

        # TODO: This is a ChatGPT solution and can be improved by using
        interval_us = 1000  # 1 ms
        register = channel_name
        start_time = time.time()
        prev_value = ljm.eReadName(self.handle, register)
        interval_handle = 1  # Use 1 as the interval handle ID
        ljm.startInterval(interval_handle, interval_us)
        try:
            while time.time() - start_time < timeout_s:
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


def edge_detect(handle, channel):
    import time

    # Configure  for rising edge timing
    ljm.eWriteName(handle, f"{channel}_EF_ENABLE", 0)  # Disable first
    ljm.eWriteName(handle, f"{channel}_EF_INDEX", 4)  # Mode 4 = Rising Edge Timing
    ljm.eWriteName(handle, f"{channel}_EF_ENABLE", 1)  # Enable

    print(f"Waiting for rising edges on {channel}...")

    last_timestamp = 0
    while True:
        timestamp = ljm.eReadName(handle, "DIO0_EF_READ_A")
        if timestamp != last_timestamp:
            print(f"Edge detected at timestamp: {timestamp}")
            last_timestamp = timestamp
        time.sleep(0.01)  # Adjust polling rate as needed


if __name__ == "__main__":
    try:
        logger.debug("Starting LabJack T4 device...")
        t4 = LabJackT4()
        available_clock_channels = t4.get_available_output_clock_channels()

        t4.add_continuous_clock_channel(
            sample_rate_hz=40,
            channel_name=available_clock_channels[1],
            enable_now=False,
        )

        t4.add_continuous_clock_channel(
            sample_rate_hz=20,
            channel_name=available_clock_channels[0],
            enable_now=False,
        )

        print(t4)

        input_trigger_channel = t4.get_available_input_start_trigger_channels()[0]
        timeout = 20  # s

        logger.debug(
            f"Waiting for input trigger on channel {input_trigger_channel} for {timeout} s"
        )
        if t4.wait_for_trigger_edge(input_trigger_channel, timeout_s=timeout):
            logger.debug(f"Detected input trigger on channel {input_trigger_channel}")
            t4.start_continuous_clocks()

        else:
            logger.debug("No input detected")
    except Exception as e:
        logger.error(str(e))
