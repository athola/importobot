"""Utilities for timestamp comparison in test suites.

Used in the ``touch.robot`` test suite to compare ``stat`` and ``date``.

``date``: date +"%Y-%m-%d %H:%M:%S.%N %z"
``stat``: stat -c %x ${filename}
"""

from datetime import datetime


def convert_timestamp(timestamp):
    """Convert timestamp in the form %Y-%m-%d %H:%M:%S.%N %z.

    to %Y-%m-%d %H:%M:%S.
    """
    # Embedded devices (and other archs) do not always
    # guarantee nanoseconds
    fmt = "%Y-%m-%d %H:%M:%S"
    datetime_, _ = timestamp.split(".", 1)
    return datetime.strptime(f"{datetime_}", fmt)


def compare_timestamps(ts1, ts2, drift):
    """Compare two timestamps and ensure the difference does not exceed drift.

    Args:
        ts1 (str): timestamp one.
        ts2 (str): timestamp two.
        drift (int, str): max difference between ts1 and ts2.

    Returns:
        None (implicit), or raises a ValueError.
    """
    ts1_fmt = convert_timestamp(ts1)
    ts2_fmt = convert_timestamp(ts2)
    time_diff = abs(ts1_fmt - ts2_fmt).total_seconds()
    exception_msg = f"{drift} between {ts1} and {ts2} exceeded"
    # typecast to float due to total_seconds() returning
    # a float
    if time_diff > float(drift):
        raise ValueError(exception_msg)
