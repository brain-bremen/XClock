from xclock.devices.daq_device import ClockDaqDevice, EdgeType

import logging

logger = logging.getLogger(__name__)


class DummyDaqDevice(ClockDaqDevice):
    @staticmethod
    def get_available_input_start_trigger_channels() -> tuple[str, ...]:
        return ("FOOIO4", "FOOIO5")

    @staticmethod
    def get_available_output_clock_channels() -> tuple[str, ...]:
        return ("FOOCLK1", "FOOCLK2")

    def add_clock_channel(
        self,
        sample_rate_hz: int,
        channel_name: str | None = None,
        enable_now: bool = True,
    ):
        logger.info(
            f"Adding clock channel {channel_name} at {sample_rate_hz} Hz, "
            f"enabled: {enable_now}"
        )

    def wait_for_trigger_edge(
        self,
        channel_name: str,
        timeout_s: float = 5.0,
        edge_type: EdgeType = EdgeType.RISING,
    ) -> bool:
        logger.info(
            f"Waiting for {edge_type.value} edge on {channel_name} "
            f"for up to {timeout_s} seconds"
        )
        import time

        time.sleep(2)

        return True
