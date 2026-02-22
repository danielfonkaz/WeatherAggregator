from datetime import datetime, timezone
from typing import List, Any


def epoch_timestamp_to_iso_format(timestamp_epoch: int) -> str:
    """Converts a Unix epoch timestamp to an ISO 8601 formatted string.

        The conversion ensures the resulting string is UTC-aligned and follows
        the standard ISO format (YYYY-MM-DDTHH:MM:SS+00:00).

        Args:
            timestamp_epoch: The integer Unix timestamp (seconds since the epoch).

        Returns:
            A string representing the date and time in ISO 8601 format.
    """
    return datetime.fromtimestamp(timestamp_epoch, tz=timezone.utc).isoformat()


def remove_list_dups(lst: List[Any]) -> List[Any]:
    """
        Removes duplicate elements from a list while preserving order.

        This function leverages the property of Python dictionaries (3.7+)
        where keys are unique and maintain insertion order. It is more
        efficient than manual loops for large datasets.

        Args:
            lst (List[Any]): The input list containing potential duplicates.

        Returns:
            List[Any]: A new list containing only unique elements from the
                original list, in the order they first appeared.

        Example:
            >>> remove_list_dups([1, 2, 2, 3, 1])
            [1, 2, 3]
    """
    return list(dict.fromkeys(lst))
