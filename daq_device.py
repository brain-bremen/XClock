from abc import ABC, abstractmethod


class OutputClockChannel:
    channel_name: str
    clock_frequency: int


class DaqDevice(ABC):
    @staticmethod
    @abstractmethod
    def get_available_input_clock_channels() -> list[str] | None:
        pass

    @staticmethod
    @abstractmethod
    def get_available_input_start_trigger_channels() -> list[str] | None:
        pass

    @staticmethod
    @abstractmethod
    def get_available_output_clock_channels() -> list[str] | None:
        pass

    @staticmethod
    @abstractmethod
    def get_available_output_barcode_channels() -> list[str] | None:
        pass

    @abstractmethod
    def start_output_clocks_now(
        self, output_channels: list[OutputClockChannel]
    ) -> None:
        pass

    @abstractmethod
    def start_output_clocks_on_input_trigger(
        self, output_channels: list[OutputClockChannel], trigger_channel: str
    ):
        pass

    # @abstractmethod
    # def add_digital_output_channel(self, port, line_grouping):
    #     pass

    # @abstractmethod
    # def add_digital_input_channel(self, port, line_grouping):
    #     pass

    # @abstractmethod
    # def add_clock_channel(self, sample_rate, port=None, line_grouping=None, on_time=None, off_time=None)->str:
    #     pass

    # @abstractmethod
    # def start(self):
    #     pass

    # @abstractmethod
    # def get_timestamps(self):
    #     pass

    # @abstractmethod
    # def reset(self):
    #     pass
