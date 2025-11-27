import logging
import time
from pathlib import Path
from typing import List

from xclock.devices.daq_device import ClockChannel, ClockDaqDevice, EdgeType

logger = logging.getLogger(__name__)


class DummyDaqDevice(ClockDaqDevice):
    def __init__(self):
        self.handle = 0  # Dummy handle
        self.base_clock_frequency_hz = 80000000  # 80 MHz dummy base frequency
        self._clock_channels: List[ClockChannel] = []
        self._next_clock_id = 0
        self._clocks_running = False

    @staticmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        return ("FOOIO4", "FOOIO5")

    @staticmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        return ("FOOCLK1", "FOOCLK2")

    def get_added_clock_channels(self) -> list[ClockChannel]:
        """Return list of added clock channels."""
        return self._clock_channels.copy()

    def get_unused_clock_channel_names(self) -> list[str]:
        """Return list of channel names that are available but not yet used."""
        available_channels = list(self.get_available_output_clock_channels())
        used_channels = [channel.channel_name for channel in self._clock_channels]
        return [ch for ch in available_channels if ch not in used_channels]

    def add_clock_channel(
        self,
        clock_tick_rate_hz: int | float,
        channel_name: str | None = None,
        number_of_pulses: int | None = None,
        duration_s: float | None = None,
        enable_clock_now: bool = False,
    ) -> ClockChannel:
        """Add a clock channel to the device."""
        # Check for mutual exclusivity of duration_s and number_of_pulses
        if duration_s is not None and number_of_pulses is not None:
            raise ValueError(
                "duration_s and number_of_pulses are mutually exclusive. Provide only one."
            )

        # Auto-calculate number of pulses from duration if provided
        if duration_s is not None:
            number_of_pulses = int(duration_s * clock_tick_rate_hz)
            logger.debug(
                f"Auto-calculated {number_of_pulses} pulses from duration {duration_s}s at {clock_tick_rate_hz} Hz"
            )

        # Auto-select channel if not specified
        if channel_name is None:
            unused_channels = self.get_unused_clock_channel_names()
            if not unused_channels:
                raise RuntimeError("No unused clock channels available")
            channel_name = unused_channels[0]

        # Validate channel name
        if channel_name not in self.get_available_output_clock_channels():
            raise ValueError(f"Channel {channel_name} is not available")

        # Check if channel already in use
        if channel_name in [ch.channel_name for ch in self._clock_channels]:
            raise ValueError(f"Channel {channel_name} is already in use")

        logger.info(
            f"Adding clock channel {channel_name} at {clock_tick_rate_hz} Hz, "
            f"pulses: {number_of_pulses}, enabled: {enable_clock_now}"
        )

        # Create clock channel
        clock_channel = ClockChannel(
            channel_name=channel_name,
            clock_id=self._next_clock_id,
            clock_enabled=enable_clock_now,
            actual_sample_rate_hz=int(clock_tick_rate_hz),  # Dummy: assume exact rate
            number_of_pulses=number_of_pulses,
        )

        self._clock_channels.append(clock_channel)
        self._next_clock_id += 1

        return clock_channel

    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        """Wait for trigger edge on specified channel."""
        if channel_name not in self.get_available_input_start_trigger_channels():
            raise ValueError(
                f"Channel {channel_name} is not available for trigger input"
            )

        logger.info(
            f"Waiting for {edge_type.value} edge on {channel_name} "
            f"for up to {timeout_s} seconds"
        )

        # Simulate waiting for trigger
        time.sleep(min(2.0, timeout_s))

        # Always return True for dummy implementation
        logger.info(f"Trigger edge detected on {channel_name}")
        return True

    def start_clocks(
        self,
        wait_for_pulsed_clocks_to_finish: bool = False,
    ):
        """Start all added clock channels."""
        if not self._clock_channels:
            logger.warning("No clock channels to start")
            return

        logger.info(f"Starting {len(self._clock_channels)} clock channels")

        # Enable all clocks
        for channel in self._clock_channels:
            channel.clock_enabled = True

        self._clocks_running = True

        if wait_for_pulsed_clocks_to_finish:
            # Calculate maximum pulse duration
            max_duration = 0.0
            for channel in self._clock_channels:
                if channel.number_of_pulses is not None:
                    duration = channel.number_of_pulses / channel.actual_sample_rate_hz
                    max_duration = max(max_duration, duration)

            if max_duration > 0:
                logger.info(f"Waiting {max_duration:.3f}s for pulsed clocks to finish")
                time.sleep(max_duration)

                # Disable pulsed clocks after they finish
                for channel in self._clock_channels:
                    if channel.number_of_pulses is not None:
                        channel.clock_enabled = False

    def start_clocks_and_record_edge_timestamps(
        self,
        wait_for_pulsed_clocks_to_finish: bool = True,
        extra_channels: list[str] = [],
        filename: Path | str | None = None,
    ):
        """Start clocks and record edge timestamps to file."""
        if filename is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = (
                Path.home()
                / "Documents"
                / "XClock"
                / f"dummy_timestamps_{timestamp}.csv"
            )

        filename = Path(filename)
        filename.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting clocks and recording timestamps to {filename}")

        # Start clocks
        self.start_clocks(
            wait_for_pulsed_clocks_to_finish=wait_for_pulsed_clocks_to_finish,
        )

        # Generate dummy timestamp data
        with open(filename, "w") as f:
            f.write("timestamp,channel,edge_type\n")

            # Simulate some dummy timestamps
            current_time = time.time()
            for i, channel in enumerate(
                self._clock_channels
                + [ClockChannel(ch, -1, True, 1000) for ch in extra_channels]
            ):
                # Generate a few dummy timestamps per channel
                for j in range(5):
                    timestamp = current_time + i * 0.1 + j * 0.01
                    edge_type = "rising" if j % 2 == 0 else "falling"
                    f.write(f"{timestamp:.6f},{channel.channel_name},{edge_type}\n")

        logger.info(f"Timestamp recording completed: {filename}")

    def stop_clocks(self):
        """Stop all running clocks."""
        logger.info("Stopping all clocks")

        for channel in self._clock_channels:
            channel.clock_enabled = False

        self._clocks_running = False

    def clear_clocks(self):
        """Clear all clock channels."""
        logger.info("Clearing all clock channels")

        self.stop_clocks()
        self._clock_channels.clear()
        self._next_clock_id = 0
