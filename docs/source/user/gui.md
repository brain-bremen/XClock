# Graphical User Interface

XClock provides a graphical user interface for users who prefer a visual way to configure and control clock generation.

## Installation

The GUI is installed automatically with the XClock package. No additional steps are required.

## Launching the GUI

Start the GUI from the command line:

```bash
xclock-gui
```

Or from Python:

```python
from gui.main import main
main()
```

## GUI Overview

The XClock GUI provides an intuitive interface for:

- Configuring multiple clock channels
- Setting clock frequencies and durations
- Starting and stopping clocks
- Recording timestamps
- Monitoring device status

## Main Window

<!-- TODO: Add screenshot here -->
```{note}
Screenshot placeholder - GUI screenshot will be added here
```

## Features

### Device Selection

Select your DAQ device from the dropdown menu:

- LabJack T4
- Dummy DAQ Device (for testing)

The GUI automatically detects and connects to available devices.

### Clock Configuration

#### Adding Clocks

1. Click the **"Add Clock"** button
2. Select an available output channel
3. Enter the desired frequency in Hz
4. Choose clock mode:
   - **Continuous**: Runs until manually stopped
   - **Pulsed**: Specify number of pulses or duration

#### Clock Parameters

- **Frequency (Hz)**: Clock tick rate (1-1000000 Hz)
- **Channel**: Output channel (FIO0, FIO1, etc.)
- **Number of Pulses**: Exact pulse count (optional)
- **Duration (seconds)**: Auto-calculates pulse count (optional)

#### Removing Clocks

Click the **"Remove"** button next to any configured clock to delete it.

### Control Buttons

#### Start

Start all configured clocks simultaneously.

Options:
- **Start Now**: Begin immediately
- **Wait for Trigger**: Wait for external trigger signal

#### Stop

Stop all running clocks immediately.

#### Clear All

Remove all configured clocks.

### Timestamp Recording

Enable **"Record Timestamps"** to save edge timing data:

- Checkbox: Enable/disable recording
- Output location: `~/Documents/XClock/`
- File format: CSV with three columns:
  - Column 1: Device-relative timestamp in nanoseconds
  - Column 2: Edge type (positive=rising, negative=falling)
  - Column 3: Unix timestamp in nanoseconds (host system time)

### Status Display

The status panel shows:

- Device connection status
- Currently running clocks
- Number of pulses generated
- Elapsed time
- Error messages and warnings

## Common Workflows

### Workflow 1: Simple Clock Test

1. Launch `xclock-gui`
2. Click **"Add Clock"**
3. Set frequency to `100` Hz
4. Set duration to `5` seconds
5. Click **"Start"**
6. Observe the status display

### Workflow 2: Multi-Camera Synchronization

1. Click **"Add Clock"** for Camera 1
   - Frequency: `60` Hz
   - Duration: `300` seconds (5 minutes)
2. Click **"Add Clock"** for Camera 2
   - Frequency: `30` Hz
   - Duration: `300` seconds
3. Enable **"Record Timestamps"**
4. Click **"Start"**
5. Wait for completion
6. Load timestamp file for analysis

### Workflow 3: Trigger-Based Start

1. Configure your clocks
2. Select **"Wait for Trigger"** option
3. Click **"Start"**
4. GUI waits for trigger signal on DIO4
5. Clocks start when trigger detected

## Troubleshooting

### GUI Won't Start

**Problem**: `xclock-gui` command not found or fails to start

**Solutions**:
- Verify XClock is installed: `pip list | grep XClock`
- Check Python GUI dependencies are installed
- Try running from Python: `python -m gui.main`

### Device Not Detected

**Problem**: "No device found" error in GUI

**Solutions**:
- Check USB connection
- Verify device drivers installed
- Click **"Refresh Devices"** button
- Restart the GUI

### Clocks Don't Start

**Problem**: Clicking "Start" doesn't generate clocks

**Solutions**:
- Verify at least one clock is configured
- Check device connection status
- Review error messages in status panel
- Try stopping and restarting

### Timestamp File Not Created

**Problem**: No CSV file generated after recording

**Solutions**:
- Verify **"Record Timestamps"** is checked
- Check output directory exists and is writable
- Look in `~/Documents/XClock/` for files
- Check status panel for error messages

## Tips

### Quick Testing

Use the GUI for quick tests and parameter exploration. Once you know your settings, automate with CLI or Python for production runs.

### Save Configurations

The GUI remembers your last configuration. Your clock settings persist between sessions.

## See Also

- {doc}`quickstart` - Basic usage patterns
- {doc}`cli` - Command-line interface
- {doc}`devices` - Device-specific information
- {doc}`../api/devices` - Python API reference