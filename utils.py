from datetime import datetime, timezone


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
