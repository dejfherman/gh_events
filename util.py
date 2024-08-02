import numpy as np
from model import Event
from datetime import timedelta


def avg_created_diff(events: list[Event], decimals=2) -> str:
    """Returns a numerical string representing the average diff between two events from the events list.
    Returns 0 if a proper result cannot be calculated.
    """
    if len(events) < 2:
        # too few events
        return "0"
    event_time_diffs = np.diff(np.array([event.created_at for event in events], dtype='datetime64[s]'))
    diff_in_seconds = np.average(event_time_diffs / np.timedelta64(1, 's'))
    return '{:.2f}'.format(abs(diff_in_seconds), decimals)
