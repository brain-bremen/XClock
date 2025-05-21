from abc import ABC, abstractmethod


class DaqDevice(ABC):
    pass

    @abstractmethod
    @staticmethod
    def get_available_output_clock_channels() -> list[str]:
        pass

    @abstractmethod
    @staticmethod
    def get_available_input_clock_channels() -> list[str]:
        pass

    @abstractmethod
    @staticmethod
    def get_available_input_start_channels() -> list[str]:
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
