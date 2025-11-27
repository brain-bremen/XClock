from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EdgeType(Enum):
    RISING = "rising"
    FALLING = "falling"


@dataclass
class ClockChannel:
    channel_name: str
    clock_id: int
    clock_enabled: bool
    actual_sample_rate_hz: int
    number_of_pulses: int | None = None


class ClockDaqDevice(ABC):
    handle: int | None
    base_clock_frequency_hz: int | float

    # TODO: These static methods should be non-static as they are more useful
    # when they actually reflect whats available right now.

    @staticmethod
    @abstractmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        pass

    @staticmethod
    @abstractmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        pass

    @abstractmethod
    def get_added_clock_channels(self) -> list[ClockChannel]:
        pass

    @abstractmethod
    def get_unused_clock_channel_names(self) -> list[str]:
        pass

    @abstractmethod
    def add_clock_channel(
        self,
        clock_tick_rate_hz: int | float,
        channel_name: str | None = None,
        number_of_pulses: int | None = None,  # None: continuous output
        duration_s: float | None = None,  # Auto-calculate pulses from duration
        enable_clock_now: bool = False,
    ) -> ClockChannel:
        pass

    @abstractmethod
    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        pass

    @abstractmethod
    def start_clocks(
        self,
        wait_for_pulsed_clocks_to_finish: bool = False,
    ):
        pass

    @abstractmethod
    def start_clocks_and_record_edge_timestamps(
        self,
        wait_for_pulsed_clocks_to_finish: bool = True,  # if there are pulsed clocks, extend wait duration until pulsed clocks are finished
        extra_channels: list[str] = [],
        filename: Path
        | str
        | None = None,  # if no filename given, will be generated automatically in ~/Documents/XClock
    ):
        pass

    @abstractmethod
    def stop_clocks(self):
        pass

    @abstractmethod
    def clear_clocks(self):
        pass

    @abstractmethod
    def close(self):
        pass
