# Installation

This guide covers the installation of XClock and its prerequisites.

## Prerequisites

### System Requirements

- **Python**: Version 3.12 or higher
- **Operating System**: Windows, macOS, or Linux
- **DAQ Device Drivers**: Device-specific software (see below)

### DAQ Device Software

Before installing XClock, you need to install the software for your DAQ device.

#### LabJack T4/T7/T8

If you're using a LabJack T-series device (T4, T7, or T8):

1. Download and install the LabJack LJM (LabJack Modbus) software from the [LabJack Downloads page](https://support.labjack.com/docs/ljm-software-installer-downloads-t4-t7-t8-digit)
2. Follow the installation instructions for your operating system
3. Verify the installation by connecting your device and using the LabJack Kipling software (included with LJM)

```{note}
The LJM software includes drivers, example code, and the Kipling utility for testing your device.
```

## Installing XClock

There are several methods to install XClock:

### Method 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager that we recommend for installing XClock.

```bash
# Add XClock to your project
uv add git+https://github.com/brain-bremen/XClock.git

# Or run directly without installation
uvx git+https://github.com/brain-bremen/XClock.git
```

### Method 2: Using pip

```bash
pip install git+https://github.com/brain-bremen/XClock.git
```

### Method 3: Development Installation

If you want to contribute to XClock or modify the source code:

```bash
# Clone the repository
git clone https://github.com/brain-bremen/XClock.git
cd XClock

# Install in editable mode with development dependencies
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"
```

## Verifying Installation

After installation, verify that XClock is installed correctly:

### Test Command-Line Tool

```bash
xclock --help
```

You should see the help message with available commands and options.

### Test Python Import

```python
from xclock.devices import LabJackT4

# This should work without errors
print("XClock imported successfully!")
```

### Test Device Connection (Optional)

If you have a LabJack T4 connected:

```python
from xclock.devices import LabJackT4

try:
    t4 = LabJackT4()
    print(f"Successfully connected to LabJack T4")
    print(f"Available channels: {t4.get_available_output_clock_channels()}")
    t4.close()
except Exception as e:
    print(f"Failed to connect: {e}")
```

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'xclock'`

**Solution**: Make sure XClock is installed in your current Python environment. Check with:

```bash
pip list | grep XClock
# or
uv pip list | grep XClock
```

### LabJack Connection Issues

**Problem**: Cannot connect to LabJack device

**Solutions**:

1. Verify LJM software is installed correctly
2. Check USB connection
3. Test device with LabJack Kipling software
4. On Linux, you may need to set up udev rules for USB access
5. Try running with sudo/administrator privileges (temporarily, to diagnose)

### Permission Issues on Linux

If you get permission errors when accessing the LabJack device on Linux:

1. Create a udev rule for LabJack devices:

```bash
sudo nano /etc/udev/rules.d/99-labjack.rules
```

2. Add the following line:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0cd5", MODE="0666"
```

3. Reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

4. Reconnect your LabJack device

## Next Steps

- Read the {doc}`quickstart` guide to start using XClock
- Explore {doc}`cli` for command-line usage
- Check {doc}`devices` for device-specific information