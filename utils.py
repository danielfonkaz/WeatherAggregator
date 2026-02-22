from datetime import datetime, timezone
from itertools import groupby
from typing import List, Any, Iterable


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


def remove_adjacent_dups(seq: Iterable[Any]) -> List[Any]:
    """
        Removes consecutive duplicate elements from a sequence.

        This function collapses adjacent identical items into a single instance,
        similar to the 'uniq' command in Unix. Non-adjacent duplicates are
        preserved.

        Args:
            seq (Iterable[Any]): An iterable sequence of items (list, string, etc.).

        Returns:
            List[Any]: A list where no two consecutive elements are the same.

        Example:
            >>> remove_adjacent_dups([1, 2, 2, 3, 3, 3, 2, 1, 1])
            [1, 2, 3, 2, 1]
            >>> remove_adjacent_dups("AAAABBBCCDAA")
            ['A', 'B', 'C', 'D', 'A']
    """
    return [key for key, _ in groupby(seq)]
