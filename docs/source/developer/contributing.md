# Contributing to XClock

Thank you for your interest in contributing to XClock! This guide will help you get started with development and explain our contribution process.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- **Python 3.12 or higher**
- **Git** for version control
- **uv** package manager (recommended) or pip
- **DAQ device** (optional, for hardware testing)

### Development Setup

1. **Fork and clone the repository:**

```bash
git clone https://github.com/YOUR-USERNAME/XClock.git
cd XClock
```

2. **Set up development environment:**

```bash
# Using uv (recommended)
uv sync --all-extras

# Or using pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

3. **Verify installation:**

```bash
# Run tests
pytest

# Check code can import
python -c "from xclock.devices import LabJackT4; print('OK')"
```

### Project Structure

```
XClock/
├── src/
│   ├── xclock/          # Core library
│   │   ├── devices/     # Device implementations
│   │   ├── edge_detection.py
│   │   └── errors.py
│   ├── cli/             # Command-line interface
│   └── gui/             # Graphical interface
├── tests/               # Test suite
│   └── xclock/
├── examples/            # Example scripts
├── docs/                # Documentation (Sphinx)
├── resources/           # Images, diagrams
└── pyproject.toml       # Project configuration
```

## Development Workflow

### 1. Create a Branch

Create a feature branch for your changes:

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
```

**Branch naming conventions:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 2. Make Changes

- Write clear, readable code
- Follow existing code style
- Add docstrings to functions and classes
- Update documentation as needed

### 3. Write Tests

All new features and bug fixes should include tests:

```python
# tests/xclock/test_my_feature.py
import pytest
from xclock.devices import LabJackT4


def test_my_new_feature():
    """Test description."""
    device = LabJackT4()
    # Test code here
    assert expected == actual
    device.close()
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/xclock/test_labjack.py

# Run with coverage
pytest --cov=xclock --cov-report=html
```

### 5. Update Documentation

If you've added features or changed APIs:

```bash
cd docs
make html
# View docs in build/html/index.html
```

### 6. Commit Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add feature: multi-device synchronization

- Implement DeviceGroup class
- Add sync_all() method
- Update documentation
- Add tests

Closes #123"
```

**Commit message format:**
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed description (wrap at 72 chars)
- Reference issues with "Closes #123" or "Fixes #456"

### 7. Push and Create Pull Request

```bash
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub:
- Provide clear description of changes
- Reference related issues
- Include examples if applicable
- Add screenshots for UI changes

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Imports**: Organized in groups (stdlib, third-party, local)
- **Quotes**: Double quotes for strings

### Type Hints

Use type hints for function signatures:

```python
def add_clock_channel(
    self,
    clock_tick_rate_hz: int | float,
    channel_name: str | None = None,
    number_of_pulses: int | None = None,
) -> ClockChannel:
    """Add a clock channel."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_frequency(base_hz: float, divisor: int) -> float:
    """
    Calculate output frequency from base clock and divisor.
    
    Args:
        base_hz: Base clock frequency in Hz
        divisor: Clock divisor value
    
    Returns:
        Output frequency in Hz
    
    Raises:
        ValueError: If divisor is zero or negative
    
    Example:
        >>> calculate_frequency(80_000_000, 256)
        312500.0
    """
    if divisor <= 0:
        raise ValueError("Divisor must be positive")
    return base_hz / divisor
```

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `LabJackT4`, `ClockChannel`)
- **Functions/methods**: `snake_case` (e.g., `add_clock_channel`, `start_clocks`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_CHANNELS`, `DEFAULT_TIMEOUT`)
- **Private members**: Prefix with `_` (e.g., `_configure_hardware`)

## Testing Guidelines

### Test Organization

- One test file per module: `test_<module_name>.py`
- Group related tests in classes
- Use descriptive test names: `test_<what>_<condition>_<expected>`

### Writing Good Tests

```python
def test_add_clock_channel_with_valid_frequency_succeeds():
    """Test that adding a clock with valid frequency succeeds."""
    # Arrange
    device = LabJackT4()
    channels = device.get_available_output_clock_channels()
    
    # Act
    clock = device.add_clock_channel(
        clock_tick_rate_hz=100,
        channel_name=channels[0],
    )
    
    # Assert
    assert clock is not None
    assert clock.channel_name == channels[0]
    assert clock.actual_sample_rate_hz > 0
    
    # Cleanup
    device.close()
```

### Test Coverage

Aim for:
- **80%+ overall coverage**
- **100% coverage for critical paths**
- Test both success and failure cases
- Test edge cases and boundary conditions

### Mocking Hardware

For tests that don't require real hardware:

```python
from unittest.mock import Mock, patch

def test_without_hardware():
    """Test without requiring actual DAQ device."""
    with patch('xclock.devices.labjack_devices.ljm') as mock_ljm:
        mock_ljm.openS.return_value = 1  # Mock handle
        
        device = LabJackT4()
        # Test code here
```

## Documentation

### Writing Documentation

Documentation is built with Sphinx and uses Markdown (MyST):

- **User guides**: `docs/source/user/`
- **Developer guides**: `docs/source/developer/`
- **API reference**: `docs/source/api/`

### Building Documentation Locally

```bash
cd docs
make html
# Open build/html/index.html in browser
```

### Documentation Style

- Use clear, simple language
- Include code examples
- Add screenshots for GUI features
- Link to related sections with `{doc}`

Example:

```markdown
## Adding a Clock

To add a clock, use the `add_clock_channel()` method:

\```python
from xclock.devices import LabJackT4

t4 = LabJackT4()
t4.add_clock_channel(clock_tick_rate_hz=100, duration_s=10)
\```

See {doc}`quickstart` for more examples.
```

## Pull Request Guidelines

### Before Submitting

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- Added feature X
- Fixed bug in Y
- Updated documentation for Z

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code reviewed
- [ ] No breaking changes (or documented)
```

### Review Process

1. Automated tests run via GitHub Actions
2. Maintainers review code
3. Address review comments
4. Merge when approved

## Adding New Features

### Device Support

See {doc}`adding_devices` for detailed guide on adding new DAQ devices.

### New CLI Commands

1. Add command function to `src/cli/main.py`
2. Register in argument parser
3. Update CLI documentation
4. Add tests

### GUI Features

1. Update GUI implementation in `src/gui/`
2. Add user documentation
3. Include screenshots
4. Test on multiple platforms if possible

## Bug Reports

### Creating Good Bug Reports

Include:

- **XClock version**: `xclock --version` or check `pyproject.toml`
- **Python version**: `python --version`
- **Operating system**: Windows/macOS/Linux
- **Device**: Which DAQ device you're using
- **Steps to reproduce**: Minimal code to trigger the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full traceback if applicable

Example:

```markdown
**Environment:**
- XClock version: 0.3.0-dev
- Python: 3.12.0
- OS: Ubuntu 22.04
- Device: LabJack T4

**Steps to reproduce:**
\```python
from xclock.devices import LabJackT4
t4 = LabJackT4()
t4.add_clock_channel(clock_tick_rate_hz=0)  # Invalid frequency
\```

**Expected:** Should raise XClockValueError
**Actual:** Program crashes with AttributeError

**Traceback:**
\```
Traceback (most recent call last):
  ...
\```
```

## Feature Requests

When requesting features:

1. Check existing issues first
2. Describe the use case
3. Provide examples of desired API
4. Explain why existing features don't work

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update CHANGELOG
3. Create release branch: `release/v0.x.0`
4. Test thoroughly
5. Merge to main
6. Tag release: `git tag v0.x.0`
7. Push tag: `git push --tags`
8. GitHub Actions builds and publishes

## Community

### Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Questions and ideas
- **Email**: maintainers (see `pyproject.toml`)

### Recognition

Contributors are recognized in:
- Release notes
- CONTRIBUTORS.md file
- Git history

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

If you have questions about contributing:

1. Check this guide and other documentation
2. Search existing issues
3. Ask in GitHub Discussions
4. Contact maintainers

Thank you for contributing to XClock! 🎉