"""
Test CORE_TIMER rollover handling in LabJackEdgeStreamer with mocked hardware.

This test exercises the actual rollover detection method in the LabJackEdgeStreamer class
by calling _process_timer_data_with_rollover_detection() directly.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np

from xclock.devices.labjack_devices import LabJackEdgeStreamer


def test_rollover_in_actual_streamer():
    """Test rollover detection using actual LabJackEdgeStreamer class with mocked hardware."""

    UINT32_MAX = 2**32

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as f:
        temp_filename = f.name

    try:
        with patch("xclock.devices.labjack_devices.ljm") as mock_ljm:
            mock_ljm.eStreamStop = MagicMock()

            streamer = LabJackEdgeStreamer(
                handle=999,
                channel_names=["DIO0", "DIO1"],
                internal_clock_sampling_rate_hz=40_000_000,
                scan_rate_hz=1000,
                filename=temp_filename,
            )

            streamer._file.close()  # pyright: ignore[reportPrivateUsage]

            assert hasattr(streamer, "_timer_rollover_count")
            assert hasattr(streamer, "_timer_offset")
            assert streamer._timer_rollover_count == 0  # pyright: ignore[reportPrivateUsage]
            assert streamer._timer_offset == 0  # pyright: ignore[reportPrivateUsage]
            assert hasattr(streamer, "_process_timer_data_with_rollover_detection")

            batch1_timer = np.array(
                [UINT32_MAX - 300, UINT32_MAX - 200, UINT32_MAX - 100],
                dtype=np.int64,
            )
            batch1_data = np.column_stack([np.zeros(3), np.zeros(3), batch1_timer])

            processed_batch1 = streamer._process_timer_data_with_rollover_detection(  # pyright: ignore[reportPrivateUsage]
                batch1_data
            )

            assert streamer._timer_rollover_count == 0
            assert streamer._timer_offset == 0
            assert np.array_equal(processed_batch1[:, -1], batch1_timer)

            streamer._last_row = processed_batch1[[-1], :].copy()
            streamer._last_row[0, -1] -= streamer._timer_offset

            batch2_timer = np.array([50, 150, 250], dtype=np.int64)
            batch2_data = np.column_stack([np.zeros(3), np.zeros(3), batch2_timer])

            processed_batch2 = streamer._process_timer_data_with_rollover_detection(
                batch2_data
            )

            assert streamer._timer_rollover_count == 1
            assert streamer._timer_offset == UINT32_MAX

            expected_corrected = batch2_timer + UINT32_MAX
            assert np.array_equal(processed_batch2[:, -1], expected_corrected)
            assert np.all(processed_batch2[:, -1] > streamer._last_row[0, -1])

            streamer._last_row = processed_batch2[[-1], :].copy()
            streamer._last_row[0, -1] -= streamer._timer_offset

            batch3_timer = np.array([350, 450, 550], dtype=np.int64)
            batch3_data = np.column_stack([np.zeros(3), np.zeros(3), batch3_timer])

            processed_batch3 = streamer._process_timer_data_with_rollover_detection(
                batch3_data
            )

            assert streamer._timer_rollover_count == 1
            assert streamer._timer_offset == UINT32_MAX

            expected_corrected = batch3_timer + UINT32_MAX
            assert np.array_equal(processed_batch3[:, -1], expected_corrected)

            streamer._last_row = processed_batch3[[-1], :].copy()
            streamer._last_row[0, -1] -= streamer._timer_offset

            batch4_timer = np.array(
                [UINT32_MAX - 200, UINT32_MAX - 100, UINT32_MAX - 50],
                dtype=np.int64,
            )
            batch4_data = np.column_stack([np.zeros(3), np.zeros(3), batch4_timer])

            processed_batch4 = streamer._process_timer_data_with_rollover_detection(
                batch4_data
            )

            assert streamer._timer_rollover_count == 1

            streamer._last_row = processed_batch4[[-1], :].copy()
            streamer._last_row[0, -1] -= streamer._timer_offset

            batch5_timer = np.array([25, 50, 75], dtype=np.int64)
            batch5_data = np.column_stack([np.zeros(3), np.zeros(3), batch5_timer])

            processed_batch5 = streamer._process_timer_data_with_rollover_detection(
                batch5_data
            )

            assert streamer._timer_rollover_count == 2
            assert streamer._timer_offset == 2 * UINT32_MAX

            expected_corrected = batch5_timer + 2 * UINT32_MAX
            assert np.array_equal(processed_batch5[:, -1], expected_corrected)
            assert np.all(processed_batch5[:, -1] > streamer._last_row[0, -1])

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


if __name__ == "__main__":
    test_rollover_in_actual_streamer()
