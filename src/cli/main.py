from enum import IntEnum, StrEnum
from dataclasses import dataclass
from xclock.devices import ClockDaqDevice, LabJackT4


class SupportedDaqDevices(StrEnum):
    lj_t4 = "LabJackT4"


device_class_map: dict[SupportedDaqDevices, ClockDaqDevice] = {
    SupportedDaqDevices.lj_t4: LabJackT4
}


def main():
    print("nothing here yet")


if __name__ == "__main__":
    main()
