import logging

import numpy as np

logger = logging.getLogger(__name__)


def detect_edges_along_columns(
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
        data = np.concatenate((prepend, data), axis=0)

    transitions = np.diff(data, axis=0)

    number_of_transitions = sum(
        (transitions[:, :number_of_data_columns] != 0).flatten()
    )

    # timestamp x channel/column number
    edge_timestamps = np.zeros(shape=(number_of_transitions, 2), dtype=np.int64)

    current_row_index = 0
    for channel_index in range(number_of_data_columns):
        rising_indices = np.where(transitions[:, channel_index] == 1)[0]
        edge_timestamps[
            current_row_index : current_row_index + rising_indices.size, 0
        ] = data[rising_indices + 1, -1]
        edge_timestamps[
            current_row_index : current_row_index + rising_indices.size, 1
        ] = channel_index + 1
        current_row_index += rising_indices.size

        falling_indices = np.where(transitions[:, channel_index] == -1)[0]
        edge_timestamps[
            current_row_index : current_row_index + falling_indices.size, 0
        ] = data[falling_indices + 1, -1]
        edge_timestamps[
            current_row_index : current_row_index + falling_indices.size, 1
        ] = -(channel_index + 1)
        current_row_index += falling_indices.size
        logger.debug(
            f"Detected {rising_indices.size} rising edges on channel {channel_index}"
        )

    # sort by timestamp (TODO: Is this in-place?)
    edge_timestamps = edge_timestamps[edge_timestamps[:, 0].argsort(), :]

    return edge_timestamps
