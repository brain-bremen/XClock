# Pseudo main file


from enum import IntEnum, StrEnum
from dataclasses import dataclass
from daq_device import DaqDevice
from labjack_devices import LabJackT4


class SupportedDaqDevices(StrEnum):
    lj_t4 = "LabJackT4"


device_class_map: dict[SupportedDaqDevices, DaqDevice] = {
    SupportedDaqDevices.lj_t4: LabJackT4
}


class StartMode(IntEnum):
    IMMEDIATE = 0
    ON_TTL = 1


class RecordingMode(IntEnum):
    NUMBER_OF_PULSES = 0
    DURATION = 1


@dataclass
class XClockConfig:
    ttl_trigger: int = 0
    device: DaqDevice | None = None


@dataclass
class RecordingConfig:
    mode: RecordingMode
    recording_id: str  # base of filename


class XClockApp:
    def __init__(self, config: XClockConfig | None = None):
        pass

    def start_recording_on_ttl(self, filename: str, ttl=None):
        pass

    def start_recording(self, config: RecordingConfig):
        pass
