"""Custom exception hierarchy for the Weather Aggregator application.

This module defines a structured set of exceptions used to handle service-level
and provider-specific failures. By inheriting from a common base class,
it allows the application to distinguish between generic Python errors
and managed weather service exceptions.

Example:
    try:
        data = fetch_weather(city)
    except WeatherServiceError as e:
        logger.error(f"Weather service failed: {e}")
"""


class WeatherServiceError(Exception):
    """Base class for any exception raised by a weather service.

        Catching this exception will intercept any error specifically defined
        within this application, regardless of the underlying service provider.
    """
    pass
