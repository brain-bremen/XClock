# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.3.1 - 2025-12-01

### Fixed

- The "verbose logging" option in the GUI had no effect.
- Cancelling the timestamp recording could cause error messages.

## 0.3.0 - 2025-11-30

### Added
- Documentation on Read the Docs
- Tkinter-based GUI for controlling clocks (`xclock-gui` command)
- Auto-computation of number of pulses based on duration

### Changed
- Improved handling of device closing after clocks are finished/cancelled

### Fixed
- CORE_TIMER rollover detection and handling

## [0.2.1] - 2025-07-07

### Added
- Delay before starting clocks when streaming to prevent loss of edges
- Host timestamp as UNIX timestamp to stream output file

### Changed
- Better filename formatting for timestamp CSV file
- Add 100 ms delay after pulsed clocks are finished to capture edges

## [0.2.0] - 2025-07-03

### Added
- CLI argument to detect edges on extra channels
- Skeleton implementation for LabJack U3 device support
- LabJackPython dependency for U series LabJack devices
- Wiring diagram for LabJack T4 in documentation

### Changed
- Clarified dependencies in `pyproject.toml`
- Updated README.md to show LabJack T4 wiring diagram
- Moved to Python 3.11 as minimum version

## [0.1.0] - 2025-07-01

### Added
- Initial release of XClock
- Support for LabJack T4 as clock device
- Multiple synchronized clock frequency outputs
- Timestamp recording for clock pulses
- CLI tool (`xclock`) for command-line control
