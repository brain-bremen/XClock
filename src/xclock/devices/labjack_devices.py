import logging
from enum import IntEnum
import time
import labjack.ljm as ljm
import copy
from xclock.devices.daq_device import ClockDaqDevice, EdgeType, ClockChannel
from xclock.errors import XClockException, XClockValueError

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExtendedFeatureIndices(IntEnum):
    PWM_OUT_FEATURE_INDEX = 0
    PWM_OUT_WITH_PHASE_EF_INDEX = 1
    PULSE_OUT_EF_INDEX = 2


class DigIoRegisters:
    channel: str  # DIO#

    def __init__(self, channel: str):
        self.channel = channel

    @property
    def enable_extended_feature(self) -> str:
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

    @property
    def read_a(self) -> str:
        return f"{self.channel}_EF_READ_A"

    @property
    def read_b(self) -> str:
        return f"{self.channel}_EF_READ_B"


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

    @property
    def count(self):
        return f"DIO_EF_CLOCK{self.clock_id}_COUNT"


def _write_register_dict_to_ljm(handle, config: dict[str, int]):
    ljm.eWriteNames(
        handle=handle,
        numFrames=len(config),
        aNames=config.keys(),
        aValues=config.values(),
    )


def _reset_output_channels(handle: int, channel_names: list[str]):
    ljm.eWriteNames(
        handle=handle,
        numFrames=len(channel_names),
        aNames=channel_names,
        aValues=[0] * len(channel_names),
    )

    for channel in channel_names:
        ljm.eWriteName(handle, DigIoRegisters(channel).enable_extended_feature, 0)

    logger.debug(f"Reset output channels {channel_names} to LOW, no EF")


def _enable_clocks(handle: int, clock_ids: list[int] = [0], enable: bool = True):
    ljm.eWriteNames(
        handle,
        len(clock_ids),
        [ClockRegisters(id).enable for id in clock_ids],
        [int(enable)] * len(clock_ids),
    )


def _read_clock_counters(handle: int, clock_ids: list[int]) -> list[int]:
    return ljm.eReadNames(
        handle,
        numFrames=len(clock_ids),
        aNames=[ClockRegisters(clock_id=id).count for id in clock_ids],
    )


def _configure_channel_to_use_as_clock(
    handle: int,
    roll_value: int,  # = base_clock_frequency // divisor // sample_rate_hz
    channel_name: str,
    clock_id: int,
    number_of_pulses: int | None = None,  # None = continuous
    enable_clock_now: bool = False,
):
    registers = DigIoRegisters(channel_name)

    duty_cycle = round(0.5 * roll_value)

    # disable, as we cannot change index if enabled
    ljm.eWriteName(handle, registers.enable_extended_feature, 0)

    # set channel to LOW to warrant proper signal generation
    ljm.eWriteName(handle=handle, name=registers.channel, value=0)

    # DIO_EF_CLOCK0_ENABLE = 0 // Disable the clock during config
    _enable_clocks(handle=handle, clock_ids=[clock_id], enable=False)

    feature_index = (
        ExtendedFeatureIndices.PWM_OUT_FEATURE_INDEX
        if number_of_pulses is None
        else ExtendedFeatureIndices.PULSE_OUT_EF_INDEX
    )

    feature_configC = 0
    if feature_index == ExtendedFeatureIndices.PULSE_OUT_EF_INDEX:
        feature_configC = number_of_pulses

    config = {
        registers.feature_index: feature_index,
        registers.clock_source: clock_id,
        registers.feature_configA: duty_cycle,
        registers.feature_configB: 1,
        registers.feature_configC: feature_configC,
    }

    _write_register_dict_to_ljm(handle, config)

    if enable_clock_now:
        config = {
            registers.enable_extended_feature: 1,
            ClockRegisters(clock_id=clock_id).enable: 1,
        }
        _write_register_dict_to_ljm(handle, config)


def _configure_clock(
    handle, clock_id: int, divisor: int, roll_value: int, enable: bool = False
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

    _write_register_dict_to_ljm(handle, clock_config)


def _set_output_channels_state(handle: int, channel_names: list[str], state: int):
    # read previous value to make sure its configured as digital

    # ljm.eWriteName(handle, channel_names, state)
    ljm.eWriteNames(
        handle=handle,
        numFrames=len(channel_names),
        aNames=channel_names,
        aValues=[state] * len(channel_names),
    )
    logger.debug(f"Set output channels {channel_names} to {state}")


class LabJackT4(ClockDaqDevice):
    """LabJack T4 device class

    Supports two clock signals on FIO6/DIO6 and FIO7/DIO7. The base clock
    frequency is 80 MHz.

    """

    # clock signals can be given out on these channels
    available_output_clock_channels = ("DIO6", "DIO7")

    @staticmethod
    def get_available_output_clock_channels():
        return LabJackT4.available_output_clock_channels

    def get_added_clock_channels(self) -> list[ClockChannel]:
        return copy.copy(self._clock_channels)

    def get_unused_clock_channel_names(self) -> list[str]:
        return list(self._unused_clock_channel_names)

    avilable_output_const_channels = ("DIO5",)

    # the device can wait for triggers on these channels
    availabile_input_trigger_channels = ("DIO4",)

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
    _clock_on_indicator_channel: str  # channel that is ON during clock output

    def __init__(self):
        try:
            self.handle = ljm.openS("T4", "ANY", "ANY")
        except Exception as e:
            self.handle = None
            logger.error(f"Failed to open LabJack T4: {str(e)}")
            raise XClockException(f"{e}")

        (self.deviceType, self.connectionType, self.serialNumber, _, _, _) = (
            ljm.getHandleInfo(self.handle)
        )
        assert self.deviceType == ljm.constants.dtT4, "Device is not a LabJack T4"

        connectionTypeString = (
            "USB" if self.connectionType == ljm.constants.ctUSB else "Ethernet"
        )
        logger.info(
            f"Opened LabJack T4 with serial number {self.serialNumber} via {connectionTypeString}"
        )

        self._clock_on_indicator_channel = LabJackT4.avilable_output_const_channels[0]

        _reset_output_channels(
            self.handle,
            list(self.get_available_output_clock_channels())
            + [self._clock_on_indicator_channel],
        )

        # disable clock0 as its mutually exclusive with CLOCK1 and CLOCK2
        _enable_clocks(self.handle, [0], False)

        self._unused_clock_channel_names = set(
            LabJackT4.available_output_clock_channels
        )

    def start_clocks(self, wait_for_pulsed_clocks_to_finish: bool = True):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")

        if len(self._clock_channels) == 0:
            raise XClockException(
                "No clock channels configured. Use add_clock_channel() first"
            )

        config = {DigIoRegisters(self._clock_on_indicator_channel).channel: 1}
        for channel in self._clock_channels:
            config[DigIoRegisters(channel.channel_name).enable_extended_feature] = 1
            config[ClockRegisters(channel.clock_id).enable] = 1
            channel.clock_enabled = True

        _write_register_dict_to_ljm(handle=self.handle, config=config)

        pulsed_clocks = [
            channel
            for channel in self._clock_channels
            if channel.number_of_pulses is not None
        ]
        if wait_for_pulsed_clocks_to_finish and len(pulsed_clocks) > 0:
            register_names = [
                (
                    DigIoRegisters(clock.channel_name).read_a,
                    DigIoRegisters(clock.channel_name).read_b,
                )
                for clock in pulsed_clocks
            ]
            isDone = [False] * len(register_names)
            while not all(isDone):
                for index, channel_register in enumerate(register_names):
                    completed, target = ljm.eReadNames(
                        self.handle,
                        len(channel_register),
                        aNames=channel_register,
                    )
                    if completed >= target:
                        isDone[index] = True
            for clock in pulsed_clocks:
                clock.clock_enabled = False

    def stop_clocks(self):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")

        registers = (
            [
                ClockRegisters(channel.clock_id).enable
                for channel in self._clock_channels
            ]
            + [
                DigIoRegisters(channel.channel_name).enable_extended_feature
                for channel in self._clock_channels
            ]
            + [channel.channel_name for channel in self._clock_channels]
        )
        registers.append(self._clock_on_indicator_channel)
        ljm.eWriteNames(
            self.handle,
            numFrames=len(registers),
            aNames=registers,
            aValues=[0] * len(registers),
        )
        for clock in self._clock_channels:
            clock.clock_enabled = False

    def add_clock_channel(
        self,
        clock_tick_rate_hz: int | float,
        channel_name: str | None = None,
        number_of_pulses: int | None = None,  # None: continuous output
        enable_clock_now: bool = False,
    ) -> ClockChannel:
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")
        if len(self._unused_clock_channel_names) == 0:
            raise XClockException(
                "No more clock channels available. Used channels: {self._used_clock_channels}"
            )

        f_min = self.base_clock_frequency / self.divisor / 2**16
        f_max = self.base_clock_frequency / self.divisor / 2

        if clock_tick_rate_hz <= f_min or clock_tick_rate_hz >= f_max:
            raise XClockValueError(
                f"Clock tick rate {clock_tick_rate_hz} Hz is out of range. "
                f"Must be between {f_min} and {f_max} Hz."
            )

        if channel_name is None:
            channel_name = self._unused_clock_channel_names.pop()

        self._unused_clock_channel_names.discard(channel_name)

        if channel_name not in self.get_available_output_clock_channels():
            raise XClockValueError(
                f"Invalid clock channel name {channel_name}. Must be in {self.get_available_output_clock_channels()}"
            )

        clock_id = (
            len(self._used_clock_channel_names) + 1
        )  # CLOCK1 and CLOCK2 are used for PWM
        roll_value = (
            self.base_clock_frequency // self.divisor // int(clock_tick_rate_hz)
        )
        _configure_clock(
            handle=self.handle,
            clock_id=clock_id,
            divisor=self.divisor,
            roll_value=roll_value,
        )
        actual_sample_rate = self.base_clock_frequency // self.divisor // roll_value

        _configure_channel_to_use_as_clock(
            handle=self.handle,
            roll_value=roll_value,
            channel_name=channel_name,
            clock_id=clock_id,
            enable_clock_now=enable_clock_now,
            number_of_pulses=number_of_pulses,
        )

        self._used_clock_channel_names.add(channel_name)
        logger.debug(
            f"Added clock channel {channel_name} with sample rate {clock_tick_rate_hz}"
        )

        self._clock_channels.append(
            ClockChannel(
                channel_name=channel_name,
                clock_id=clock_id,
                clock_enabled=enable_clock_now,
                actual_sample_rate_hz=actual_sample_rate,
                number_of_pulses=number_of_pulses,
            )
        )
        return self._clock_channels[-1]

    def remove_clock_channel(self, channel_name: str):
        pass

    def __str__(self):
        out = f"LabJack T4 with handle {self.handle}:\n"
        for channel in self._clock_channels:
            out += f"\t- {str(channel)}\n"
        out += f"\t- Clock On Indicator: {self._clock_on_indicator_channel}"
        return out

    def __del__(self):
        if self.handle:
            channels_to_disable = []
            channels_to_disable.extend([ch.channel_name for ch in self._clock_channels])
            channels_to_disable.extend([self._clock_on_indicator_channel])
            ljm.eWriteNames(
                handle=self.handle,
                numFrames=len(channels_to_disable),
                aNames=channels_to_disable,
                aValues=[0] * len(channels_to_disable),
            )
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

    def clear_clocks(self):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")

        self.stop_clocks()
        self._clock_channels[:] = []
        self._used_clock_channel_names.clear()
        self._unused_clock_channel_names = set(
            LabJackT4.available_output_clock_channels
        )


async def record_incoming_trigger_timestamps(
    self, channels: list[str] = [], sampling_interval_ms: int = 1
):
    # TODO: poll channels in interval and record rising and falling edges
    # This should potentially be async to be able to run while giving
    # other commands, e.g. start an ouput clock
    pass


if __name__ == "__main__":
    try:
        logger.debug("Starting LabJack T4 device...")
        t4 = LabJackT4()
        available_clock_channels = t4.get_available_output_clock_channels()

        t4.add_clock_channel(
            clock_tick_rate_hz=100,
            channel_name=available_clock_channels[0],
            enable_clock_now=False,
            number_of_pulses=200,
        )

        t4.add_clock_channel(
            clock_tick_rate_hz=50,
            channel_name=available_clock_channels[1],
            enable_clock_now=False,
            number_of_pulses=50,
        )

        print(t4)

        # start clocks and measure time until done
        start_time = time.time()
        t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)
        elapsed = time.time() - start_time
        print(f"start_clocks returned after {elapsed:.3f} seconds")
        exit()

        input_trigger_channel = t4.get_available_input_start_trigger_channels()[0]
        timeout = 20  # s

        logger.debug(
            f"Waiting for input trigger on channel {input_trigger_channel} for {timeout} s"
        )
        if t4.wait_for_trigger_edge(input_trigger_channel, timeout_s=timeout):
            logger.debug(f"Detected input trigger on channel {input_trigger_channel}")
            t4.start_clocks()

        else:
            logger.debug("No input detected")
    except Exception as e:
        logger.error(str(e))
