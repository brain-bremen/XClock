from abc import ABC, abstractmethod

class ClockDaqDevice(ABC):

    @abstractmethod
    def add_digital_output_channel(self, port, line_grouping):
        pass

    @abstractmethod
    def add_digital_input_channel(self, port, line_grouping):
        pass

    @abstractmethod
    def add_clock_channel(self, sample_rate, port=None, line_grouping=None, on_time=None, off_time=None)->str:
        pass

    @abstractmethod
    def start(self):
        pass
    
    @abstractmethod
    def get_timestamps(self):
        pass

    @abstractmethod
    def reset(self):
        pass

