"""Launcher script for XClock GUI."""


def main():
    """Entry point for the XClock GUI application."""
    # Import and run the GUI main function
    from gui.main import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
