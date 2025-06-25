from abc import ABC, abstractmethod
from enum import Enum


class EdgeType(Enum):
    RISING = "rising"
    FALLING = "falling"


class DaqDevice(ABC):
    @staticmethod
    @abstractmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        pass

    @staticmethod
    @abstractmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        pass

    @abstractmethod
    def add_continuous_clock_channel(
        self,
        sample_rate_hz: int,
        channel_name: str | None = None,
        enable_now: bool = True,
    ):
        pass

    @abstractmethod
    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        pass
