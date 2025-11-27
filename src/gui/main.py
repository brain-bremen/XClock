import logging
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Optional

from xclock.devices import ClockDaqDevice, DummyDaqDevice, LabJackT4
from xclock.errors import XClockException, XClockValueError

# Device mapping
DEVICE_MAP = {
    "LabJack T4": LabJackT4,
    "Dummy DAQ Device": DummyDaqDevice,
}


def check_device_availability(device_class):
    """Check if a device is available by attempting to initialize it."""
    try:
        device = device_class()
        # Close/cleanup the device if it has a close method
        if hasattr(device, "close"):
            device.close()
        return True
    except Exception:
        return False


def get_available_devices():
    """Get a dictionary of available devices."""
    available = {}
    for name, device_class in DEVICE_MAP.items():
        if check_device_availability(device_class):
            available[name] = device_class
    return available


class TextHandler(logging.Handler):
    """Custom logging handler that writes to a tkinter Text widget."""

    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.configure(state="disabled")
            self.text_widget.see(tk.END)

        # Schedule the update in the main thread
        self.text_widget.after(0, append)


class XClockGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("XClock Control Panel")
        self.root.geometry("700x600")

        self.device: Optional[ClockDaqDevice] = None
        self.is_running = False
        self.clock_thread: Optional[threading.Thread] = None
        self.available_devices = {}

        self.setup_logging()
        self.check_devices()
        self.create_widgets()

    def check_devices(self):
        """Check which devices are available."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Checking device availability...")

        for name, device_class in DEVICE_MAP.items():
            is_available = check_device_availability(device_class)
            if is_available:
                self.available_devices[name] = device_class
                self.logger.info(f"✓ {name} is available")
            else:
                self.logger.info(f"✗ {name} is not available")

        if not self.available_devices:
            self.logger.warning("No devices are available!")

    def setup_logging(self):
        """Setup logging to GUI."""
        self.logger = logging.getLogger(__name__)

        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            force=True,
        )

        # Set xclock loggers
        logging.getLogger("xclock").setLevel(logging.INFO)
        logging.getLogger("xclock.devices").setLevel(logging.INFO)

    def create_widgets(self):
        """Create GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # Device selection
        ttk.Label(main_frame, text="Device:").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )

        # Only show available devices
        available_device_names = list(self.available_devices.keys())
        default_device = available_device_names[0] if available_device_names else ""

        self.device_var = tk.StringVar(value=default_device)
        device_combo = ttk.Combobox(
            main_frame,
            textvariable=self.device_var,
            values=available_device_names,
            state="readonly" if available_device_names else "disabled",
            width=30,
        )
        device_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)

        # Add info label if some devices are unavailable
        unavailable_devices = [
            name for name in DEVICE_MAP.keys() if name not in self.available_devices
        ]
        if unavailable_devices:
            unavailable_text = f"Unavailable: {', '.join(unavailable_devices)}"
            ttk.Label(
                main_frame, text=unavailable_text, font=("", 8), foreground="gray"
            ).grid(row=row, column=2, sticky=tk.W, padx=(5, 0))

        row += 1

        # Clock tick rates
        ttk.Label(main_frame, text="Clock Rates (Hz):").grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.rates_var = tk.StringVar(value="60, 100")
        ttk.Entry(main_frame, textvariable=self.rates_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), pady=5
        )
        ttk.Label(
            main_frame, text="(comma-separated)", font=("", 8), foreground="gray"
        ).grid(row=row, column=2, sticky=tk.W, padx=(5, 0))
        row += 1

        # Duration or pulses frame
        duration_frame = ttk.LabelFrame(main_frame, text="Duration/Pulses", padding="5")
        duration_frame.grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        duration_frame.columnconfigure(1, weight=1)
        row += 1

        # Radio button selection
        self.mode_var = tk.StringVar(value="continuous")

        ttk.Radiobutton(
            duration_frame,
            text="Continuous",
            variable=self.mode_var,
            value="continuous",
            command=self.on_mode_change,
        ).grid(row=0, column=0, sticky=tk.W, pady=2)

        ttk.Radiobutton(
            duration_frame,
            text="Duration (seconds):",
            variable=self.mode_var,
            value="duration",
            command=self.on_mode_change,
        ).grid(row=1, column=0, sticky=tk.W, pady=2)

        self.duration_var = tk.StringVar(value="5.0")
        self.duration_entry = ttk.Entry(
            duration_frame, textvariable=self.duration_var, width=15
        )
        self.duration_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        self.duration_entry.config(state="disabled")

        ttk.Radiobutton(
            duration_frame,
            text="Number of Pulses:",
            variable=self.mode_var,
            value="pulses",
            command=self.on_mode_change,
        ).grid(row=2, column=0, sticky=tk.W, pady=2)

        self.pulses_var = tk.StringVar(value="300, 500")
        self.pulses_entry = ttk.Entry(
            duration_frame, textvariable=self.pulses_var, width=15
        )
        self.pulses_entry.grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=2)
        self.pulses_entry.config(state="disabled")
        ttk.Label(
            duration_frame, text="(comma-separated)", font=("", 8), foreground="gray"
        ).grid(row=2, column=2, sticky=tk.W, padx=(5, 0))

        # Advanced options
        advanced_frame = ttk.LabelFrame(
            main_frame, text="Advanced Options", padding="5"
        )
        advanced_frame.grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10
        )
        row += 1

        self.record_timestamps_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            advanced_frame,
            text="Record Edge Timestamps",
            variable=self.record_timestamps_var,
        ).grid(row=0, column=0, sticky=tk.W, pady=2)

        ttk.Label(advanced_frame, text="Extra Channels:").grid(
            row=1, column=0, sticky=tk.W, pady=2
        )
        self.extra_channels_var = tk.StringVar(value="")
        ttk.Entry(advanced_frame, textvariable=self.extra_channels_var, width=30).grid(
            row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=(5, 0)
        )
        ttk.Label(
            advanced_frame, text="(e.g., EIO4,EIO5)", font=("", 8), foreground="gray"
        ).grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
        advanced_frame.columnconfigure(1, weight=1)

        self.verbose_var = tk.BooleanVar(value=False)
        verbose_check = ttk.Checkbutton(
            advanced_frame,
            text="Verbose Logging",
            variable=self.verbose_var,
            command=self.on_verbose_change,
        )
        verbose_check.grid(row=2, column=0, sticky=tk.W, pady=2)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        self.start_button = ttk.Button(
            button_frame,
            text="Start Clocks",
            command=self.start_clocks,
            width=15,
            state="normal" if self.available_devices else "disabled",
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="Stop Clocks",
            command=self.stop_clocks,
            width=15,
            state="disabled",
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Status/Log output
        ttk.Label(main_frame, text="Log Output:").grid(
            row=row, column=0, sticky=tk.W, pady=(10, 5)
        )
        row += 1

        self.log_text = scrolledtext.ScrolledText(
            main_frame, height=15, state="disabled", wrap=tk.WORD
        )
        self.log_text.grid(
            row=row,
            column=0,
            columnspan=3,
            sticky=(tk.W, tk.E, tk.N, tk.S),
            pady=(0, 5),
        )
        main_frame.rowconfigure(row, weight=1)
        row += 1

        # Clear log button
        ttk.Button(main_frame, text="Clear Log", command=self.clear_log, width=15).grid(
            row=row, column=0, sticky=tk.W
        )

        # Add text handler to logger
        text_handler = TextHandler(self.log_text)
        text_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(text_handler)

        if not self.available_devices:
            self.logger.warning(
                "XClock GUI initialized - No devices available! Please connect a device and restart."
            )
        else:
            self.logger.info("XClock GUI initialized")

    def on_mode_change(self):
        """Handle mode change between continuous/duration/pulses."""
        mode = self.mode_var.get()

        if mode == "duration":
            self.duration_entry.config(state="normal")
            self.pulses_entry.config(state="disabled")
        elif mode == "pulses":
            self.duration_entry.config(state="disabled")
            self.pulses_entry.config(state="normal")
        else:  # continuous
            self.duration_entry.config(state="disabled")
            self.pulses_entry.config(state="disabled")

    def on_verbose_change(self):
        """Handle verbose logging toggle."""
        if self.verbose_var.get():
            logging.getLogger("xclock").setLevel(logging.DEBUG)
            logging.getLogger("xclock.devices").setLevel(logging.DEBUG)
            logging.getLogger("xclock.devices.labjack_devices").setLevel(logging.DEBUG)
            logging.getLogger().setLevel(logging.DEBUG)
        else:
            logging.getLogger("xclock").setLevel(logging.INFO)
            logging.getLogger("xclock.devices").setLevel(logging.INFO)
            logging.getLogger("xclock.devices.labjack_devices").setLevel(logging.INFO)
            logging.getLogger().setLevel(logging.INFO)

    def clear_log(self):
        """Clear the log text widget."""
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")

    def parse_clock_rates(self):
        """Parse clock rates from input."""
        try:
            rates_str = self.rates_var.get().strip()
            if not rates_str:
                raise ValueError("Clock rates cannot be empty")
            return [float(x.strip()) for x in rates_str.split(",") if x.strip()]
        except ValueError as e:
            raise XClockValueError(f"Invalid clock rates: {e}")

    def parse_pulses(self):
        """Parse number of pulses from input."""
        try:
            pulses_str = self.pulses_var.get().strip()
            if not pulses_str:
                return None
            return [int(x.strip()) for x in pulses_str.split(",") if x.strip()]
        except ValueError as e:
            raise XClockValueError(f"Invalid number of pulses: {e}")

    def create_device(self):
        """Create and initialize the selected device."""
        device_name = self.device_var.get()

        if device_name not in self.available_devices:
            raise XClockException(f"{device_name} is not available")

        device_class = self.available_devices[device_name]
        try:
            return device_class()
        except Exception as e:
            raise XClockException(f"Failed to initialize {device_name}: {e}")

    def setup_clocks(self, device, clock_rates):
        """Setup clock channels on the device."""
        if not clock_rates:
            raise XClockValueError("At least one clock rate must be specified")

        mode = self.mode_var.get()
        duration_s = None
        number_of_pulses = None

        if mode == "duration":
            try:
                duration_s = float(self.duration_var.get())
            except ValueError:
                raise XClockValueError("Invalid duration value")
        elif mode == "pulses":
            number_of_pulses = self.parse_pulses()

        # Check for mutual exclusivity
        if duration_s is not None and number_of_pulses is not None:
            raise XClockValueError(
                "Duration and number of pulses are mutually exclusive"
            )

        available_channels = device.get_available_output_clock_channels()

        if len(clock_rates) > len(available_channels):
            raise XClockValueError(
                f"Too many clock rates specified ({len(clock_rates)}). "
                f"Device supports only {len(available_channels)} channels."
            )

        # Setup each clock channel
        for i, rate in enumerate(clock_rates):
            pulses = None

            if number_of_pulses is not None:
                pulses = number_of_pulses[i] if i < len(number_of_pulses) else None
            elif duration_s is not None:
                # Auto-calculate pulses from duration
                pulses = int(duration_s * rate)

            channel = device.add_clock_channel(
                clock_tick_rate_hz=rate,
                channel_name=available_channels[i],
                number_of_pulses=pulses,
                enable_clock_now=False,
            )

            if pulses is not None:
                pulse_info = f" ({pulses} pulses"
                if duration_s is not None:
                    pulse_info += f", ~{duration_s}s"
                pulse_info += ")"
            else:
                pulse_info = " (continuous)"
            self.logger.info(
                f"Added clock: {rate} Hz on {channel.channel_name}{pulse_info}"
            )

    def run_clocks(self):
        """Run the clocks in a separate thread."""
        try:
            clock_rates = self.parse_clock_rates()
            self.device = self.create_device()
            self.setup_clocks(self.device, clock_rates)

            mode = self.mode_var.get()
            has_pulsed_clocks = mode in ("duration", "pulses")

            # Handle timestamp recording
            if self.record_timestamps_var.get():
                self.logger.info("Recording edge timestamps...")
                output_dir = Path.home() / "Documents" / "XClock"
                output_dir.mkdir(parents=True, exist_ok=True)

                import time

                timestamp_str = time.strftime("%Y-%m-%d_%H-%M-%S")
                filename = output_dir / f"xclock_timestamps_{timestamp_str}.csv"

                # Parse extra channels
                extra_channels = []
                extra_str = self.extra_channels_var.get().strip()
                if extra_str:
                    extra_channels = [
                        x.strip() for x in extra_str.split(",") if x.strip()
                    ]
                    self.logger.info(
                        f"Detecting edges on additional channels: {extra_channels}"
                    )

                self.device.start_clocks_and_record_edge_timestamps(
                    wait_for_pulsed_clocks_to_finish=has_pulsed_clocks,
                    filename=filename,
                    extra_channels=extra_channels,
                )
                self.logger.info(f"Timestamps saved to: {filename}")
            else:
                self.logger.info("Starting clocks...")
                self.device.start_clocks(
                    wait_for_pulsed_clocks_to_finish=has_pulsed_clocks,
                )

            if has_pulsed_clocks:
                self.logger.info("All pulsed clocks finished.")
                # Re-enable start button after pulsed clocks finish
                self.root.after(0, self.on_clocks_finished)
            else:
                self.logger.info(
                    "Clocks running continuously. Click 'Stop Clocks' to stop."
                )

        except (XClockException, XClockValueError) as e:
            self.logger.error(f"Error: {e}")
            self.root.after(0, self.on_clocks_finished)
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            self.root.after(0, self.on_clocks_finished)

    def start_clocks(self):
        """Start clocks button handler."""
        if self.is_running:
            self.logger.warning("Clocks are already running")
            return

        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

        # Run in separate thread to avoid blocking GUI
        self.clock_thread = threading.Thread(target=self.run_clocks, daemon=True)
        self.clock_thread.start()

    def stop_clocks(self):
        """Stop clocks button handler."""
        if not self.is_running:
            self.logger.warning("No clocks are running")
            return

        try:
            if self.device:
                self.logger.info("Stopping clocks...")
                self.device.stop_clocks()
                self.logger.info("Clocks stopped.")
        except Exception as e:
            self.logger.error(f"Error stopping clocks: {e}")
        finally:
            self.on_clocks_finished()

    def on_clocks_finished(self):
        """Reset UI state when clocks finish."""
        self.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        if self.device and hasattr(self.device, "close"):
            try:
                self.device.close()
            except Exception as e:
                self.logger.error(f"Error closing device: {e}")
        
        self.device = None


def main():
    """Main entry point for GUI."""
    root = tk.Tk()
    app = XClockGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
