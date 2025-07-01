import numpy as np
import pytest
from xclock.edge_detection import detect_edges_along_columns


def test_single_rising_edge():
    # Channel 0: 0 -> 1 at t=2
    data = np.array(
        [
            [0, 0],
            [0, 1],
            [1, 2],
            [1, 3],
        ]
    )
    # 1 channel, last column is timestamp
    edges = detect_edges_along_columns(data, 1)
    expected = np.array([[2, 1]])
    np.testing.assert_array_equal(edges, expected)


def test_single_falling_edge():
    # Channel 0: 1 -> 0 at t=2
    data = np.array(
        [
            [1, 0],
            [1, 1],
            [0, 2],
            [0, 3],
        ]
    )
    edges = detect_edges_along_columns(data, 1)
    expected = np.array([[2, -1]])
    np.testing.assert_array_equal(edges, expected)


def test_rising_and_falling_edges_multiple_channels():
    # Channel 0: 0->1 at t=1, 1->0 at t=3
    # Channel 1: 0->1 at t=2, 1->0 at t=4
    data = np.array(
        [
            [0, 0, 0],
            [1, 0, 1],
            [1, 1, 2],
            [0, 1, 3],
            [0, 0, 4],
        ]
    )
    edges = detect_edges_along_columns(data, 2)
    expected = np.array(
        [
            [1, 1],  # ch0 rising
            [2, 2],  # ch1 rising
            [3, -1],  # ch0 falling
            [4, -2],  # ch1 falling
        ]
    )
    np.testing.assert_array_equal(edges, expected)


def test_no_edges():
    data = np.array(
        [
            [0, 0, 0],
            [0, 0, 1],
            [0, 0, 2],
        ]
    )
    edges = detect_edges_along_columns(data, 2)
    assert edges.shape == (0, 2)


def test_with_prepend():
    # Prepend a row to detect edge at first row
    data = np.array(
        [
            [1, 5],
            [1, 6],
        ]
    )
    prepend = np.array([[0, 4]])
    edges = detect_edges_along_columns(data, 1, prepend=prepend)
    expected = np.array([[5, 1]])
    np.testing.assert_array_equal(edges, expected)


def test_unsorted_edges_are_sorted_by_timestamp():
    # Channel 0: 0->1 at t=2
    # Channel 1: 0->1 at t=1
    data = np.array(
        [
            [0, 0, 0],
            [0, 1, 1],
            [1, 1, 2],
        ]
    )
    edges = detect_edges_along_columns(data, 2)
    expected = np.array(
        [
            [1, 2],  # ch1 rising at t=1
            [2, 1],  # ch0 rising at t=2
        ]
    )
    np.testing.assert_array_equal(edges, expected)


def test_multiple_edges_same_timestamp():
    # Both channels change at t=1
    data = np.array(
        [
            [0, 0, 0],
            [1, 1, 1],
        ]
    )
    edges = detect_edges_along_columns(data, 2)
    expected = np.array(
        [
            [1, 1],
            [1, 2],
        ]
    )
    np.testing.assert_array_equal(edges, expected)


def test_rising_and_falling_edges():
    # Channel 0: 0->1 at t=1, 1->0 at t=3
    # Channel 1: 0->1 at t=2, 1->0 at t=4
    data = np.array(
        [
            [0, 0, 0],
            [1, 0, 1],
            [1, 1, 2],
            [0, 1, 3],
            [0, 0, 4],
        ]
    )
    edges = detect_edges_along_columns(data, 2)
    expected = np.array(
        [
            [1, 1],  # ch0 rising
            [2, 2],  # ch1 rising
            [3, -1],  # ch0 falling
            [4, -2],  # ch1 falling
        ]
    )
    np.testing.assert_array_equal(edges, expected)
