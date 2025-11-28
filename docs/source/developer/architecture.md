# Architecture Overview

This document describes the architecture and design of XClock, helping developers understand how the system works internally.

## System Overview

XClock is designed with a modular architecture that separates device-specific implementations from core functionality. This allows easy addition of new DAQ devices while maintaining a consistent API.

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
├──────────────┬──────────────┬──────────────┬────────────┤
│  Python API  │  CLI Tool    │  GUI (Qt)    │  Scripts   │
└──────────────┴──────────────┴──────────────┴────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Core XClock Library (xclock)                │
├─────────────────────────────────────────────────────────┤
│  • ClockDaqDevice (Abstract Interface)                  │
│  • ClockChannel (Data Model)                            │
│  • Edge Detection & Timestamp Recording                 │
│  • Error Handling                                        │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│           Device Implementations (Drivers)               │
├──────────────┬──────────────┬──────────────┬────────────┤
│  LabJack T4  │  LabJack U3  │  Dummy DAQ   │  Future... │
└──────────────┴──────────────┴──────────────┴────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│         Hardware Abstraction Layer (SDKs)                │
├──────────────┬──────────────┬──────────────┬────────────┤
│  LabJack LJM │  PyDAQmx     │  Simulation  │  Others    │
└──────────────┴──────────────┴──────────────┴────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│              Physical Hardware (DAQ Devices)             │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Abstract Device Interface (`ClockDaqDevice`)

The `ClockDaqDevice` abstract base class defines the contract that all device implementations must follow.

**Location**: `src/xclock/devices/daq_device.py`

**Responsibilities**:
- Define interface for all clock devices
- Ensure consistent API across different hardware
- Provide type definitions (`ClockChannel`, `EdgeType`)

**Key Methods**:
- `add_clock_channel()` - Configure a clock
- `start_clocks()` - Begin clock generation
- `stop_clocks()` - Halt clock generation
- `wait_for_trigger_edge()` - Wait for external trigger
- `start_clocks_and_record_edge_timestamps()` - Record timing data

### 2. Device Implementations

Each supported DAQ device has its own implementation class.

#### LabJack T4 (`LabJackT4`)

**Location**: `src/xclock/devices/labjack_devices.py`

**Key Features**:
- 80 MHz base clock
- Hardware timer/counter configuration
- Register-based control
- Multi-channel synchronization

**Implementation Details**:
- Uses LabJack LJM (Modbus) library
- Configures DIO extended features as clocks
- Calculates divisors for frequency generation
- Manages hardware registers directly

#### Dummy DAQ Device (`DummyDaqDevice`)

**Location**: `src/xclock/devices/dummy_daq_device.py`

**Purpose**:
- Testing without hardware
- API demonstration
- Unit testing
- Development

### 3. Data Models

#### `ClockChannel`

Represents a configured clock output channel.

```python
@dataclass
class ClockChannel:
    channel_name: str              # e.g., "FIO0"
    clock_id: int                  # Unique identifier (1, 2, 3, ...)
    clock_enabled: bool            # Currently running?
    actual_sample_rate_hz: int     # Achieved frequency
    number_of_pulses: int | None   # None = continuous
```

#### `EdgeType`

Enumeration for trigger edge detection.

```python
class EdgeType(Enum):
    RISING = "rising"
    FALLING = "falling"
```

### 4. Edge Detection and Timestamp Recording

**Location**: `src/xclock/edge_detection.py`

**Purpose**: Record precise timestamps of clock edges for post-acquisition synchronization.

**Components**:
- `LabJackEdgeStreamer` - Continuous data streaming and edge detection
- Timestamp calculation with rollover handling
- CSV output formatting

**Data Flow**:
1. Start streaming from input channels
2. Detect edges in real-time
3. Calculate nanosecond timestamps
4. Write to CSV file
5. Handle timer rollover (32-bit counters)

**CSV Format**:
```
timestamp_ns, edge_type
1000000, 1          # Rising edge on clock 1
1500000, -1         # Falling edge on clock 1
2000000, 2          # Rising edge on clock 2
```

### 5. Error Handling

**Location**: `src/xclock/errors.py`

**Exception Hierarchy**:
```
Exception
└── XClockException (base)
    ├── XClockValueError
    ├── XClockDeviceError
    └── XClockTimeoutError
```

**Usage**:
- `XClockException` - General errors
- `XClockValueError` - Invalid parameters
- Device-specific exceptions as needed

## Interface Layers

### Python API Layer

Direct programmatic access to XClock functionality.

```python
from xclock.devices import LabJackT4

t4 = LabJackT4()
t4.add_clock_channel(clock_tick_rate_hz=100, duration_s=10)
t4.start_clocks(wait_for_pulsed_clocks_to_finish=True)
t4.close()
```

**Advantages**:
- Full control and flexibility
- Integration with data analysis pipelines
- Programmatic automation
- Access to all features

### CLI Layer

**Location**: `src/cli/main.py`

**Architecture**:
- Argument parsing with `argparse`
- Device mapping dictionary
- Command pattern (start, stop)
- Logging configuration

**Design Decisions**:
- Global options before commands
- Sensible defaults
- Clear error messages
- Verbose mode for debugging

### GUI Layer

**Location**: `src/gui/main.py`

**Technology**: Qt/PyQt (assumed based on project structure)

**Features**:
- Visual clock configuration
- Real-time status display
- File output management
- Device selection

## Clock Generation Algorithm

### Frequency Calculation (LabJack T4)

The LabJack T4 uses a divisor-based clock generation system:

```
Output Frequency = Base Clock / (Divisor × Roll Value)
                 = 80,000,000 Hz / (Divisor × Roll Value)
```

**Constraints**:
- Divisor ∈ {1, 2, 4, 8, 16, 32, 64, 256}
- Roll Value ∈ [1, 65535]

**Algorithm**:
1. Calculate ideal divisor = Base Clock / Target Frequency
2. Find nearest valid divisor from allowed set
3. Calculate roll value
4. Compute actual achievable frequency
5. Return `ClockChannel` with actual frequency

**Example**:
```
Target: 100 Hz
Ideal divisor = 80,000,000 / 100 = 800,000
Nearest valid divisor = 256
Roll value = 800,000 / 256 = 3,125
Actual frequency = 80,000,000 / (256 × 3,125) = 100 Hz
```

### Multi-Channel Synchronization

All clocks share the same base clock, ensuring synchronization:

1. Configure all channels (but don't start)
2. Enable all clocks simultaneously via hardware registers
3. Hardware ensures aligned start times
4. All clocks tick relative to the same time base

**Typical skew**: < 100 nanoseconds between channels

## Data Flow

### Starting Clocks

```
User Request
    │
    ▼
add_clock_channel() for each clock
    │
    ├─ Calculate actual frequency
    ├─ Allocate channel
    ├─ Create ClockChannel object
    └─ Configure hardware registers
    │
    ▼
start_clocks()
    │
    ├─ Enable all configured channels
    ├─ Start hardware timers
    └─ Optionally wait for completion
    │
    ▼
Hardware generates clock signals
```

### Recording Timestamps

```
User Request: start_clocks_and_record_edge_timestamps()
    │
    ▼
Initialize EdgeStreamer
    │
    ├─ Configure input channels
    ├─ Set up streaming
    └─ Create output file
    │
    ▼
Start clocks
    │
    ▼
EdgeStreamer runs in separate thread
    │
    ├─ Read streaming data
    ├─ Detect edges
    ├─ Calculate timestamps
    ├─ Handle rollover
    └─ Write to CSV
    │
    ▼
Wait for completion
    │
    ▼
Stop streaming and close file
```

## Design Patterns

### 1. Abstract Factory Pattern

`ClockDaqDevice` serves as an abstract factory:
- Defines interface for creating clock channels
- Concrete implementations (LabJackT4, etc.) create device-specific configurations

### 2. Strategy Pattern

Different devices implement different strategies for:
- Frequency calculation
- Hardware configuration
- Timestamp recording

### 3. Builder Pattern

`add_clock_channel()` uses builder-like pattern:
- Incremental configuration
- Validation at each step
- Returns configured object

### 4. Template Method Pattern

`start_clocks_and_record_edge_timestamps()`:
- Defines algorithm skeleton
- Subclasses fill in device-specific details

## Threading Model

### Main Thread
- User interface (CLI/GUI)
- Clock configuration
- Synchronous operations

### Background Threads
- Edge detection streaming (when recording timestamps)
- Continuous data acquisition
- File I/O for CSV writing

**Thread Safety**:
- Device handles are not thread-safe
- EdgeStreamer uses thread-safe queues
- Lock-free design where possible

## File I/O

### Timestamp CSV Files

**Location**: `~/Documents/XClock/`

**Format**:
- Plain text CSV
- Two columns: timestamp (int64), edge_type (int8)
- No header row
- Nanosecond precision

**Writing Strategy**:
- Buffered writes for performance
- Flush on completion
- Error handling for disk full

## Performance Considerations

### Timing Precision

**Sources of error**:
1. Base clock accuracy (±20 ppm for LabJack T4)
2. Divisor quantization
3. Software latency (for triggers)
4. USB communication jitter

**Mitigation**:
- Use hardware timers (not software timing)
- Synchronize to external reference if needed
- Record actual timestamps for post-processing

### Scalability

**Current limits**:
- Up to 12 simultaneous clocks (LabJack T4)
- ~1 MHz timestamp recording rate
- Limited by USB bandwidth for streaming

### Memory Usage

**Typical footprint**:
- Base library: <10 MB
- Per clock channel: <1 KB
- Timestamp buffer: Configurable

## Configuration Management

### Device Configuration
- Stored in device object
- Not persisted between runs
- CLI/GUI can save/load configurations

### Output Paths
- Default: `~/Documents/XClock/`
- Configurable via parameters
- Auto-create directories

## Testing Strategy

### Unit Tests
- Mock hardware interactions
- Test each method independently
- Validate error handling

### Integration Tests
- Use DummyDaqDevice for no-hardware testing
- Test complete workflows
- Verify file outputs

### Hardware Tests
- Require actual device
- Manual verification
- Signal measurement with oscilloscope

## Future Architecture Considerations

### Planned Enhancements

1. **Plugin System**: Dynamic device driver loading
2. **Configuration Files**: YAML/JSON device configs
3. **Remote Devices**: Network-based DAQ support
4. **Calibration**: Frequency calibration routines
5. **Visualization**: Real-time signal plotting

### Extensibility Points

- New device drivers via `ClockDaqDevice` interface
- Custom edge detectors
- Alternative output formats (HDF5, etc.)
- Network protocols for distributed systems

## Debugging

### Logging Levels

```python
DEBUG   - Detailed hardware communications
INFO    - Normal operations (start, stop, etc.)
WARNING - Frequency adjustments, retries
ERROR   - Operation failures
```

### Common Debug Points

1. Device initialization
2. Frequency calculation
3. Hardware register writes
4. Edge detection
5. File I/O

### Tools

- Built-in logging module
- Verbose CLI mode (`--verbose`)
- Hardware vendor tools (Kipling for LabJack)
- Oscilloscope for signal verification

## See Also

- {doc}`adding_devices` - Adding new device support
- {doc}`contributing` - Development guidelines
- {doc}`../api/devices` - API documentation