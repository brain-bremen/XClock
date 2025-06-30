from .devices import LabJackT4
import os.path

DEFAULT_OUTPUT_DIRECTORY = os.path.join(os.path.expanduser("~"), "Documents", "XClock")

if not os.path.exists(DEFAULT_OUTPUT_DIRECTORY):
    os.makedirs(DEFAULT_OUTPUT_DIRECTORY, exist_ok=True)
