from pathlib import Path
from xclock.devices.daq_device import ClockChannel, ClockDaqDevice, EdgeType
from u3 import U3

# TODO:
# - figure out which pins can be used for clocks, edge detection inputs and trigger output
# - implement timers (https://support.labjack.com/docs/2-9-timers-counters-u3-datasheet)
# - implement streaming


class LabJackU3(ClockDaqDevice):
    @staticmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        raise NotImplementedError()

    @staticmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        raise NotImplementedError()

    def __init__(self):
        self.u3 = U3()

    def get_added_clock_channels(self) -> list[ClockChannel]:
        raise NotImplementedError()

    def add_clock_channel(
        self,
        clock_tick_rate_hz: int | float,
        channel_name: str | None = None,
        number_of_pulses: int | None = None,
        enable_clock_now: bool = False,
    ) -> ClockChannel:
        raise NotImplementedError()

    def start_clocks(
        self,
        wait_for_pulsed_clocks_to_finish: bool = False,
        timeout_duration_s: float = 0,
    ):
        raise NotImplementedError()

    def start_clocks_and_record_edge_timestamps(
        self,
        wait_for_pulsed_clocks_to_finish: bool = True,
        timeout_duration_s: float = 0,
        extra_channels: list[str] = [],
        filename: Path | str | None = None,
    ):
        raise NotImplementedError()

    def stop_clocks(self):
        raise NotImplementedError()

    def clear_clocks(self):
        raise NotImplementedError()

    def get_unused_clock_channel_names(self) -> list[str]:
        return []

    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        raise NotImplementedError()
