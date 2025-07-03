import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional


from xclock.devices import ClockDaqDevice, LabJackT4, DummyDaqDevice
from xclock.errors import XClockException, XClockValueError

logger = logging.getLogger(__name__)

# Device mapping
DEVICE_MAP = {
    "labjackt4": LabJackT4,
    "dummydaqdevice": DummyDaqDevice,
}


def setup_logging(verbose: bool) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Force reconfigure logging to override any module-level configs
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # This ensures we override any existing configuration
    )

    # Set xclock module loggers to appropriate levels
    if verbose:
        logging.getLogger("xclock").setLevel(logging.DEBUG)
        # Also set specific module loggers that are commonly used
        logging.getLogger("xclock.devices").setLevel(logging.DEBUG)
        logging.getLogger("xclock.devices.labjack_devices").setLevel(logging.DEBUG)
        logging.getLogger("xclock.edge_detection").setLevel(logging.DEBUG)
    else:
        # Ensure INFO level for non-verbose mode
        logging.getLogger("xclock").setLevel(logging.INFO)
        logging.getLogger("xclock.devices").setLevel(logging.INFO)
        logging.getLogger("xclock.devices.labjack_devices").setLevel(logging.INFO)
        logging.getLogger("xclock.edge_detection").setLevel(logging.INFO)


def parse_comma_separated_numbers(value: str) -> List[float]:
    """Parse comma-separated numbers from string."""
    if not value:
        return []
    try:
        return [float(x.strip()) for x in value.split(",") if x.strip()]
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid number format: {e}")


def create_device(device_name: str) -> ClockDaqDevice:
    """Create and initialize a DAQ device."""
    if device_name not in DEVICE_MAP:
        raise XClockException(
            f"Unsupported device: {device_name}. Supported: {list(DEVICE_MAP.keys())}"
        )

    try:
        device_class = DEVICE_MAP[device_name]
        return device_class()
    except Exception as e:
        raise XClockException(f"Failed to initialize {device_name}: {e}")


def setup_clocks(
    device: ClockDaqDevice,
    clock_rates: List[float],
    number_of_pulses: Optional[List[int]] = None,
) -> None:
    """Setup clock channels on the device."""
    if not clock_rates:
        raise XClockValueError("At least one clock rate must be specified")

    available_channels = device.get_available_output_clock_channels()

    if len(clock_rates) > len(available_channels):
        raise XClockValueError(
            f"Too many clock rates specified ({len(clock_rates)}). "
            f"Device supports only {len(available_channels)} channels."
        )

    # Setup each clock channel
    for i, rate in enumerate(clock_rates):
        pulses = (
            number_of_pulses[i]
            if number_of_pulses and i < len(number_of_pulses)
            else None
        )

        channel = device.add_clock_channel(
            clock_tick_rate_hz=rate,
            channel_name=available_channels[i],
            number_of_pulses=pulses,
            enable_clock_now=False,
        )

        pulse_info = f" ({pulses} pulses)" if pulses else " (continuous)"
        logger.info(f"Added clock: {rate} Hz on {channel.channel_name}{pulse_info}")


def cmd_start(args) -> None:
    """Start clocks command."""
    setup_logging(args.verbose)

    try:
        # Validate that clock-tick-rates is provided for start command
        if not args.clock_tick_rates:
            raise XClockValueError(
                "--clock-tick-rates is required for the start command"
            )

        device = create_device(args.device)

        # Parse number of pulses if provided
        pulses = None
        if args.number_of_pulses:
            pulses = [
                int(x) for x in parse_comma_separated_numbers(args.number_of_pulses)
            ]

        # Setup clocks
        setup_clocks(device, args.clock_tick_rates, pulses)

        # Determine if we have pulsed clocks
        has_pulsed_clocks = pulses is not None and any(p > 0 for p in pulses)

        # Handle when to start
        if args.when == "on_trigger":
            # Wait for trigger before starting
            trigger_channels = device.get_available_input_start_trigger_channels()
            if not trigger_channels:
                raise XClockException("Device does not support trigger inputs")

            trigger_channel = trigger_channels[0]  # Use first available

            logger.info(f"Waiting for trigger on {trigger_channel}...")
            logger.info("Send a rising edge to start clocks. Press Ctrl+C to cancel.")

            # Wait for trigger
            triggered = device.wait_for_trigger_edge(
                channel_name=trigger_channel,
                timeout_s=args.timeout if args.timeout > 0 else float("inf"),
            )

            if not triggered:
                logger.info("Timeout waiting for trigger.")
                sys.exit(1)

            logger.info("Trigger received! Starting clocks...")

        # Start clocks
        if args.when == "now":
            logger.info("Starting clocks...")

        # Handle recording timestamps
        if args.record_timestamps:
            logger.info("Recording edge timestamps...")
            # Determine filename for timestamps
            output_dir = Path.home() / "Documents" / "XClock"
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = output_dir / f"xclock_timestamps_{int(time.time())}.csv"

            # Parse extra channels for edge detection if provided
            extra_channels: list[str] = []
            if args.detect_edges_on:
                extra_channels = [
                    x.strip() for x in args.detect_edges_on.split(",") if x.strip()
                ]
                logger.info(f"Detecting edges on additional channels: {extra_channels}")

            device.start_clocks_and_record_edge_timestamps(
                wait_for_pulsed_clocks_to_finish=has_pulsed_clocks,
                timeout_duration_s=args.duration if args.duration > 0 else 0.0,
                filename=filename,
                extra_channels=extra_channels,
            )
            logger.info(f"Timestamps saved to: {filename}")
        else:
            device.start_clocks(
                wait_for_pulsed_clocks_to_finish=has_pulsed_clocks,
                timeout_duration_s=args.duration if args.duration > 0 else 0.0,
            )

        if has_pulsed_clocks:
            logger.info("All pulsed clocks finished.")
        elif args.duration > 0:
            logger.info(f"Clocks ran for {args.duration} seconds.")
        elif not args.record_timestamps:
            logger.info("Clocks started. Use Ctrl+C to stop.")
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                logger.info("\nStopping clocks...")
                device.stop_clocks()

    except (XClockException, XClockValueError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled.")
        sys.exit(1)


def cmd_stop(args) -> None:
    """Stop clocks command."""
    setup_logging(args.verbose)

    try:
        device = create_device(args.device)

        logger.info("Stopping all clocks...")
        device.stop_clocks()
        logger.info("All clocks stopped.")

    except (XClockException, XClockValueError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled.")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="xclock",
        description="XClock - Tools for synchronizing experimental clocks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  xclock --clock-tick-rates 60,100 --device labjackt4 --duration 5 start
  xclock --clock-tick-rates 60,100 --device labjackt4 --number-of-pulses 200,150 start
  xclock --clock-tick-rates 60,100 --device labjackt4 --when on_trigger start
  xclock --clock-tick-rates 60,100 --device labjackt4 --record-timestamps start
  xclock --clock-tick-rates 60,100 --record-timestamps --detect_edges_on EIO4,EIO5 start
  xclock --device labjackt4 stop
        """,
    )

    # Global options
    parser.add_argument(
        "--clock-tick-rates",
        type=parse_comma_separated_numbers,
        required=False,
        help="Comma-separated list of clock rates in Hz (e.g., 60,100)",
    )

    parser.add_argument(
        "--device",
        choices=list(DEVICE_MAP.keys()),
        default="labjackt4",
        required=False,
        help="DAQ device to use (default: labjackt4)",
    )

    parser.add_argument(
        "--when",
        choices=["now", "on_trigger"],
        default="now",
        help="When to start clocks: 'now' or 'on_trigger' (default: now)",
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Duration to run clocks in seconds (0 = run until stopped)",
    )

    parser.add_argument(
        "--number-of-pulses",
        type=str,
        help="Comma-separated number of pulses for each clock (for pulsed mode)",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=0,
        help="Timeout in seconds when waiting for trigger (<=0 : no timeout)",
    )

    parser.add_argument(
        "--record-timestamps",
        action="store_true",
        help="Record edge timestamps to CSV file",
    )

    parser.add_argument(
        "--detect-edges-on",
        type=str,
        help="Comma-separated list of channels to detect edges on (e.g., EIO4,EIO5)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start clocks")
    start_parser.set_defaults(func=cmd_start)

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop all running clocks")
    stop_parser.set_defaults(func=cmd_stop)

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
