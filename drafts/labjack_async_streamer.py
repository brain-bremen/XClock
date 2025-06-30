import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import labjack.ljm as ljm
import numpy as np

from xclock import DEFAULT_OUTPUT_DIRECTORY
from xclock.devices import LabJackT4

logger = logging.getLogger(__name__)


class LabJackEdgeStreamer:
    """
    Class to stream edges from a LabJack T4 device in the background.
    This class uses the LabJack T4's streaming capabilities to monitor digital
    input channels for rising and falling edges, capturing timestamps and channel
    indices. The data is saved to a CSV file for later analysis.
    """

    t4: LabJackT4
    number_of_detected_edges: int
    internal_clock_sampling_rate_hz: int
    filename: Path | str

    def __init__(
        self, t4_device: LabJackT4, channel_names, scan_rate_hz=1000, filename=None
    ):
        self.t4 = t4_device
        self.channel_names = channel_names.copy()
        self.number_of_sampled_channels = len(channel_names)
        self.channel_names.extend(["CORE_TIMER", "STREAM_DATA_CAPTURE_16"])

        self.scan_rate = scan_rate_hz
        self.scans_per_read = int(scan_rate_hz / 2)
        self.internal_clock_sampling_rate_hz = t4_device.base_clock_frequency // 2
        self.number_of_detected_edges = 0

        if filename is None:
            self.filename = os.path.join(
                DEFAULT_OUTPUT_DIRECTORY, f"labjack_stream_{int(time.time())}.csv"
            )
        self._file = open(self.filename, "w", newline="")

        # Threading control
        self.streaming_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        self._start_streaming_timestamp = int(-1)

        self._last_row = np.zeros(
            shape=(1, self.number_of_sampled_channels + 1)
        )  # last row contains timestamps

        # make sure device is not streaming
        try:
            ljm.eStreamStop(self.t4.handle)
        except Exception as e:
            logger.warning(f"Device was already streaming:{e}")

    def __del__(self):
        self._file.close()

    def start_streaming(self):
        """Start streaming in background thread"""
        if self.is_streaming():
            logger.info("Streaming already running!")
            return

        self.stop_event.clear()
        self.streaming_thread = threading.Thread(
            target=self._streaming_loop, daemon=True
        )
        self.streaming_thread.start()
        logger.info(f"Background streaming started at {self.scan_rate} Hz")

    def stop_streaming(self):
        """Stop background streaming"""
        if self.is_streaming():
            self.stop_event.set()
            self.streaming_thread.join(timeout=2.0)  # type: ignore is_streaming asserts
            logger.info("Background streaming stopped")

    def is_streaming(self) -> bool:
        """Check if streaming is active"""
        return self.streaming_thread and self.streaming_thread.is_alive()

    def _streaming_loop(self):
        """Main streaming loop running in background thread"""
        try:
            # Setup streaming
            aScanList = ljm.namesToAddresses(
                len(self.channel_names), self.channel_names
            )[0]

            # Configure stream settings
            aNames = ["STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX"]
            aValues = [0, 0]
            ljm.eWriteNames(self.t4.handle, len(aNames), aNames, aValues)

            # Start streaming
            ljm.eStreamStart(
                handle=self.t4.handle,
                scansPerRead=self.scans_per_read,
                scanRate=self.scan_rate,
                aScanList=aScanList,
                numAddresses=len(aScanList),
            )

            self._start_streaming_timestamp = int(
                ljm.eReadName(self.t4.handle, "STREAM_START_TIME_STAMP")
            )
            self._skipped_samples = 0

            while not self.stop_event.is_set():
                # Read data
                aData, deviceScanBacklog, ljmScanBacklog = ljm.eStreamRead(
                    self.t4.handle
                )

                logger.debug(
                    f"Read {len(aData)} data points from stream backlog={deviceScanBacklog}/{ljmScanBacklog} (device/host)"
                )

                curSkip = aData.count(-9999.0)
                if curSkip > 0:
                    logger.warning(f"Skipped {curSkip} samples in this read")
                self._skipped_samples += curSkip

                # Process data
                data = np.array(aData, dtype=np.int64).reshape((-1, len(aScanList)))

                # Combine timer columns
                data[:, -2] += data[:, -1] << 16
                data = data[:, :-1]  # Drop last column

                if not (data[:, -1] >= 0).all():
                    logger.warning(
                        f"Negative timestamps detected in data: {data[:, -1]}"
                    )
                data[:, -1] -= self._start_streaming_timestamp

                # Detect edges
                edge_timestamps = _detect_edges_along_columns(
                    data,
                    number_of_data_columns=self.number_of_sampled_channels,
                    prepend=self._last_row,
                )

                self.number_of_detected_edges += edge_timestamps.shape[0]

                foo = edge_timestamps[:, 0] / (
                    self.internal_clock_sampling_rate_hz / 1e9
                )
                edge_timestamps[:, 0] = foo

                # Update last row for next iteration but keep 2d shape
                self._last_row = data[[-1], :]

                # write to file
                if self._file:
                    np.savetxt(
                        self._file,
                        edge_timestamps,
                        delimiter=",",
                        fmt="%d",
                    )
        except Exception as e:
            logger.error(f"Streaming setup error: {e}")
        finally:
            # Clean up
            try:
                ljm.eStreamStop(self.t4.handle)
            except:
                pass


def _detect_edges_along_columns(
    data, number_of_data_columns, prepend=None
) -> np.ndarray:
    """
    Detect rising and falling edges in the given data.
    Args:
        data (np.ndarray): 2D array with shape (n_samples, n_channels + 1),
                           last column contains integer timestamps used in output
        number_of_data_columns (int): Number of columns to analyze for edges
        prepend (np.ndarray, optional): Optional array to prepend to the data for edge detection.
    Returns:
        np.ndarray: 2D array with shape (n_edges, 2), where each row contains
                    [timestamp, channel_index] with the channel_index beging <0 if
                    a falling edge is detected
    """

    if prepend is not None:
        transitions = np.diff(data, axis=0, prepend=prepend)
    else:
        transitions = np.diff(data, axis=0)

    # timestamp x channel/column number
    number_of_transitions = sum(
        (transitions[:, :number_of_data_columns] != 0).flatten()
    )
    edge_timestamps = np.zeros(shape=(number_of_transitions, 2), dtype=np.int64)

    current_row_index = 0

    for channel_index in range(number_of_data_columns):
        # Rising edges
        rising_indices = np.where(transitions[:, channel_index] == 1)[0]
        edge_timestamps[
            current_row_index : current_row_index + rising_indices.size, 0
        ] = data[rising_indices, -1]
        edge_timestamps[
            current_row_index : current_row_index + rising_indices.size, 1
        ] = channel_index + 1
        current_row_index += rising_indices.size
        falling_indices = np.where(transitions[:, channel_index] == -1)[0]
        edge_timestamps[
            current_row_index : current_row_index + falling_indices.size, 0
        ] = data[falling_indices, -1]
        edge_timestamps[
            current_row_index : current_row_index + falling_indices.size, 1
        ] = -(channel_index + 1)
        current_row_index += falling_indices.size
        logger.debug(
            f"Detected {rising_indices.size} rising edges on channel {channel_index}"
        )

    foo = edge_timestamps[:, 0].argsort()
    edge_timestamps = edge_timestamps[foo, :]

    return edge_timestamps


# Usage example:
def main():
    # Setup LabJack
    t4 = LabJackT4()

    t4.add_clock_channel(100, "DIO6", number_of_pulses=200)
    t4.add_clock_channel(30, "DIO7", 90)

    channel_names = ["DIO6", "DIO7"]
    streamer = LabJackEdgeStreamer(t4, channel_names, scan_rate_hz=1000)

    streamer.start_streaming()
    t4.start_clocks()

    # Do other work...
    time.sleep(5)

    # Stop everything
    t4.stop_clocks()
    streamer.stop_streaming()

    assert streamer.number_of_detected_edges == (200 + 90) * 2


if __name__ == "__main__":
    main()
