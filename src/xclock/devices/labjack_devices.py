import copy
import logging
import os
import threading
import time
from enum import IntEnum
from pathlib import Path

import numpy as np
import labjack.ljm as ljm

from xclock.devices.daq_device import ClockChannel, ClockDaqDevice, EdgeType
from xclock.errors import XClockException, XClockValueError
from xclock.edge_detection import detect_edges_along_columns

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SKIP_VALUE = -9999.0
DEFAULT_OUTPUT_DIRECTORY = os.path.join(os.path.expanduser("~"), "Documents", "XClock")

if not os.path.exists(DEFAULT_OUTPUT_DIRECTORY):
    os.makedirs(DEFAULT_OUTPUT_DIRECTORY, exist_ok=True)


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

    Supports two clock signals on FIO6/DIO6 and FIO7/DIO7. The base clock frequency is 80
    MHz.

    DIO5/FIO5 serves as an output trigger that is active while any clock is active.

    DIO4/FIO4 can be used as additional

    For recording the timestamps, the FIO6 and FIO7 pins have to be connected to DIO14/EIO6
    and EIO15/EIO7 (on the DSUB15 connector),  respectively as directly reading out an
    output channel via streaming is not supported.

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

    base_clock_frequency_hz = 80_000_000  # 80 MHz
    divisor = 256

    handle: int | None = None
    deviceType: int
    connectionType: int
    serialNumber: int

    _used_clock_channel_names: set[str] = set()
    _unused_clock_channel_names: set[str]
    _clock_copy_channel_names: list[str] = ["EIO6", "EIO7"]
    _clock_channels: list[ClockChannel] = []
    _clock_on_indicator_channel: str  # channel that is ON during clock output
    _all_digital_channels = [f"DIO{channel}" for channel in range(4, 20)]

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

        # disable pullup on all channels (TODO: This does not seem to work on LabJack T4
        # although it is supposed to)
        # ljm.eWriteName(self.handle, "DIO_PULLUP_DISABLE", 0b111111111110000)

        # read all channels once to make sure they are digital (we're not using analog here)
        _ = ljm.eReadNames(
            self.handle,
            len(LabJackT4._all_digital_channels),
            LabJackT4._all_digital_channels,
        )

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

    def start_clocks(
        self,
        wait_for_pulsed_clocks_to_finish: bool = False,  # return before timeout if pulsed clocks are finished
        timeout_duration_s: float = 0.0,  # return after timeout if timeout > 0
    ):
        """
        Starts the configured clocks on the LabJack T4 device. This function has three
        modes:

        (1) If `wait_for_pulsed_clocks_to_finish` is True, the function will wait until all
            pulsed locks are finished (potentially forever).

        (2) If `timeout_duration_s` is >0 and ,`wait_for_pulsed_clocks_to_finish` is False,
            the function will wait until the timeout duration has passed.

        (3) If `wait_for_pulsed_clocks_to_finish` is False and `timeout_duration_s` is <= 0,
            the function will return immediately.


        """

        logger.debug(
            f"Starting clocks on {[channel.channel_name for channel in self._clock_channels]} indicator on {self._clock_on_indicator_channel}"
        )
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")

        if len(self._clock_channels) == 0:
            raise XClockException(
                "No clock channels configured. Use add_clock_channel() first"
            )

        if wait_for_pulsed_clocks_to_finish is True and timeout_duration_s > 0:
            raise XClockValueError(
                "wait_for_pulsed_clocks_to_finish cannot be True with a timeout_duration_s > 0. These options are mutually exclusive."
            )

        config = {DigIoRegisters(self._clock_on_indicator_channel).channel: 1}
        for channel in self._clock_channels:
            config[DigIoRegisters(channel.channel_name).enable_extended_feature] = 1
            config[ClockRegisters(channel.clock_id).enable] = 1
            channel.clock_enabled = True

        _write_register_dict_to_ljm(handle=self.handle, config=config)

        if wait_for_pulsed_clocks_to_finish:
            pulsed_clocks = [
                channel
                for channel in self._clock_channels
                if channel.number_of_pulses is not None
            ]
            if len(pulsed_clocks) == 0:
                return

            logger.debug(f"Waiting for pulsed clocks to finish: {pulsed_clocks}")
            register_names = [
                (
                    DigIoRegisters(clock.channel_name).read_a,
                    DigIoRegisters(clock.channel_name).read_b,
                )
                for clock in pulsed_clocks
            ]
            isDone = [False] * len(register_names)
            # t_start = time.time()
            while not all(isDone):
                for index, channel_register in enumerate(register_names):
                    completed, target = ljm.eReadNames(
                        self.handle,
                        len(channel_register),
                        aNames=channel_register,
                    )
                    if completed >= target:
                        isDone[index] = True
            ljm.eWriteName(
                self.handle, DigIoRegisters(self._clock_on_indicator_channel).channel, 0
            )
            for clock in pulsed_clocks:
                clock.clock_enabled = False
            return

        if timeout_duration_s > 0.0:
            logger.debug(f"Waiting for timeout of {timeout_duration_s} s")
            # use ljm intervals to wait for duartion
            interval_us = int(1e6 * timeout_duration_s)
            interval_handle = 1  # Use 1 as the interval handle ID
            ljm.startInterval(interval_handle, interval_us)
            try:
                ljm.waitForNextInterval(interval_handle)
            finally:
                ljm.cleanInterval(interval_handle)

            self.stop_clocks()

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

        f_min = self.base_clock_frequency_hz / self.divisor / 2**16
        f_max = self.base_clock_frequency_hz / self.divisor / 2

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
            self.base_clock_frequency_hz // self.divisor // int(clock_tick_rate_hz)
        )
        _configure_clock(
            handle=self.handle,
            clock_id=clock_id,
            divisor=self.divisor,
            roll_value=roll_value,
        )
        actual_sample_rate = self.base_clock_frequency_hz // self.divisor // roll_value

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

    def start_clocks_and_record_edge_timestamps(
        self,
        wait_for_pulsed_clocks_to_finish: bool = True,
        timeout_duration_s: float = 0.0,
        extra_channels: list[
            str
        ] = [],  # record edge timestamps also on these channels in addition to clocks
        filename: Path | str | None = None,
    ):
        if self.handle is None:
            raise XClockException("Labjack device is not initialized")
        if len(self._clock_channels) == 0:
            raise XClockException(
                "No clock channels configured. Use add_clock_channel() first"
            )

        streamer = LabJackEdgeStreamer(
            self.handle,
            list(self._clock_copy_channel_names) + extra_channels,
            internal_clock_sampling_rate_hz=self.base_clock_frequency_hz // 2,
            scan_rate_hz=10000,
            filename=filename,
        )

        streamer.start_streaming()
        time.sleep(0.5)
        self.start_clocks(
            wait_for_pulsed_clocks_to_finish=wait_for_pulsed_clocks_to_finish,
            timeout_duration_s=timeout_duration_s,
        )

        self.stop_clocks()
        streamer.stop_streaming()

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


class LabJackEdgeStreamer:
    """
    Class to stream edges from a LabJack T4 device in the background.
    This class uses the LabJack T4's streaming capabilities to monitor digital
    input channels for rising and falling edges, capturing timestamps and channel
    indices. The data is saved to a CSV file in ~/Documents/XClock for later analysis.
    """

    handle: int
    number_of_detected_edges: int
    internal_clock_sampling_rate_hz: int
    filename: Path | str

    def __init__(
        self,
        handle: int,
        channel_names: list[str],
        internal_clock_sampling_rate_hz: int | float,
        scan_rate_hz=1000,
        filename=None,
    ):
        self.handle = handle
        self.channel_names = channel_names.copy()
        self.number_of_sampled_channels = len(channel_names)
        self.channel_names.extend(["CORE_TIMER", "STREAM_DATA_CAPTURE_16"])

        self.scan_rate = scan_rate_hz
        self.scans_per_read = int(scan_rate_hz / 2)
        self.internal_clock_sampling_rate_hz = internal_clock_sampling_rate_hz
        self.number_of_detected_edges = 0

        if filename is None:
            timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.join(
                DEFAULT_OUTPUT_DIRECTORY, f"labjack_stream_{timestamp_str}.csv"
            )

        self.filename = filename
        self._file = open(self.filename, "w", newline="")

        # Threading control
        self.streaming_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()

        self._start_streaming_timestamp = int(-1)

        self._last_row = np.zeros(shape=(1, self.number_of_sampled_channels + 1))

        try:
            ljm.eStreamStop(self.handle)
        except Exception as e:
            pass

    def __del__(self):
        self._file.close()

    def start_streaming(self):
        """Start streaming in background thread"""
        if self.is_streaming():
            logger.info("Streaming already running!")
            return
        self.stop_event.clear()
        self.streaming_thread = threading.Thread(
            target=self._streaming_loop, daemon=True
        )
        self.streaming_thread.start()
        logger.debug("Waiting for streaming thread to become ready")
        result = self.ready_event.wait(5)
        if not result:
            raise XClockException(f"Could not start edge detector thread")
        logger.info(
            f"Start background streaming and edge detection on {self.channel_names[:-2]} at {self.scan_rate} Hz"
        )

    def stop_streaming(self):
        """Stop background streaming"""
        if self.is_streaming():
            self.stop_event.set()
            self.streaming_thread.join(timeout=2.0)  # type: ignore is_streaming asserts
            logger.info("Background streaming stopped")

    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self.streaming_thread and self.streaming_thread.is_alive()

    def _streaming_loop(self):
        """Main streaming loop running in background thread"""
        try:
            # Setup streaming
            aScanList = ljm.namesToAddresses(
                len(self.channel_names), self.channel_names
            )[0]

            aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
            aValues = [0, 0]
            ljm.eWriteNames(self.handle, len(aNames), aNames, aValues)

            ljm.eStreamStart(
                handle=self.handle,
                scansPerRead=self.scans_per_read,
                scanRate=self.scan_rate,
                aScanList=aScanList,
                numAddresses=len(aScanList),
            )

            self._start_streaming_timestamp = int(
                ljm.eReadName(self.handle, "STREAM_START_TIME_STAMP")
            )
            self._skipped_samples = 0
            while not self.stop_event.is_set():
                current_host_timestamp = np.int64(time.time() * 1e9)  # in nanoseconds
                aData, deviceScanBacklog, ljmScanBacklog = ljm.eStreamRead(self.handle)
                # if self.ready_event.is_set()
                self.ready_event.set()

                logger.debug(
                    f"Read {len(aData)} data points from stream backlog={deviceScanBacklog}/{ljmScanBacklog} (device/host)"
                )

                curSkip = aData.count(SKIP_VALUE)
                if curSkip > 0:
                    logger.warning(f"Skipped {curSkip} samples in this read")
                self._skipped_samples += curSkip

                data = np.array(aData, dtype=np.int64).reshape((-1, len(aScanList)))

                # Combine 2 x 16 bit timer columns
                data[:, -2] += data[:, -1] << 16
                data = data[:, :-1]  # Drop last column

                # data[:, -1] -= self._start_streaming_timestamp

                edge_timestamps = detect_edges_along_columns(
                    data,
                    number_of_data_columns=self.number_of_sampled_channels,
                    prepend=self._last_row,
                )

                self.number_of_detected_edges += edge_timestamps.shape[0]

                # convert timestamps to nanoseconds
                edge_timestamps[:, 0] = edge_timestamps[:, 0] / (
                    self.internal_clock_sampling_rate_hz / 1e9
                )

                # Update last row for next iteration but keep 2d shape
                self._last_row = data[[-1], :]

                # add host timestamp as last column to data before writing to disk
                edge_timestamps = np.hstack(
                    (
                        edge_timestamps,
                        np.full(
                            (edge_timestamps.shape[0], 1),
                            current_host_timestamp,
                            dtype=np.int64,
                        ),
                    )
                )

                if self._file:
                    np.savetxt(
                        self._file,
                        edge_timestamps,
                        delimiter=",",
                        fmt="%d",
                    )
        except Exception as e:
            logger.error(f"Streaming setup error: {e}")
        finally:
            # Clean up
            try:
                ljm.eStreamStop(self.handle)
            except:
                pass


if __name__ == "__main__":
    try:
        logger.debug("Starting LabJack T4 device...")
        t4 = LabJackT4()
        available_clock_channels = t4.get_available_output_clock_channels()

        t4.add_clock_channel(
            clock_tick_rate_hz=75,
            channel_name=available_clock_channels[0],
            enable_clock_now=False,
            number_of_pulses=10,
        )

        t4.add_clock_channel(
            clock_tick_rate_hz=30,
            channel_name=available_clock_channels[1],
            enable_clock_now=False,
            number_of_pulses=5,
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
