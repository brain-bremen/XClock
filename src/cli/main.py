import argparse
import logging
import sys
import time
from typing import List, Optional


from xclock.devices import ClockDaqDevice, LabJackT4
from xclock.errors import XClockException, XClockValueError

logger = logging.getLogger(__name__)

# Device mapping
DEVICE_MAP = {
    "labjackt4": LabJackT4,
}


def setup_logging(verbose: bool) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


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

        # Start clocks
        logger.info("Starting clocks...")
        device.start_clocks(
            wait_for_pulsed_clocks_to_finish=has_pulsed_clocks,
            timeout_duration_s=args.duration if args.duration > 0 else 0.0,
        )

        if has_pulsed_clocks:
            logger.info("All pulsed clocks finished.")
        elif args.duration > 0:
            logger.info(f"Clocks ran for {args.duration} seconds.")

        else:
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


def cmd_wait_for_trigger(args) -> None:
    """Wait for trigger command."""
    setup_logging(args.verbose)

    try:
        device = create_device(args.device)

        # Setup clocks but don't start them
        setup_clocks(device, args.clock_tick_rates)

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

        if triggered:
            logger.info("Trigger received! Starting clocks...")
            device.start_clocks(wait_for_pulsed_clocks_to_finish=True)
            logger.info("Clocks finished.")
        else:
            logger.info("Timeout waiting for trigger.")
            sys.exit(1)

    except (XClockException, XClockValueError) as e:
        logger.error(f"Error: {e}", file=sys.stderr)
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
  xclock --clock-tick-rates 60,100 --device labjackt4 start --duration 5
  xclock --clock-tick-rates 60,100 --device labjackt4 --number-of-pulses 200,150 start
  xclock --clock-tick-rates 60,100 --device labjackt4 wait-for-trigger
        """,
    )

    # Global options
    parser.add_argument(
        "--clock-tick-rates",
        type=parse_comma_separated_numbers,
        required=True,
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
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start clocks")
    start_parser.add_argument(
        "--duration",
        type=float,
        default=0,
        help="Duration to run clocks in seconds (0 = run until stopped)",
    )
    start_parser.add_argument(
        "--number-of-pulses",
        type=str,
        help="Comma-separated number of pulses for each clock (for pulsed mode)",
    )
    start_parser.set_defaults(func=cmd_start)

    # Wait-for-trigger command
    trigger_parser = subparsers.add_parser(
        "wait-for-trigger", help="Wait for trigger to start clocks"
    )
    trigger_parser.add_argument(
        "--timeout", type=float, default=0, help="Timeout in seconds (<=0 : no timeout)"
    )
    trigger_parser.set_defaults(func=cmd_wait_for_trigger)

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
