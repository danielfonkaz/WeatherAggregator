"""OpenMeteo Service Provider Module.

This module implements the integration with the Open-Meteo.com service.
It provides functional utilities for fetching real-time weather data,
structured data models for internal consumption, and a specialized
exception hierarchy to handle API-specific failure modes.

The module follows a clean separation of concerns:
    1. Exception handling for network and logic errors.
    2. Data modeling via the OpenMeteoResponse class.
    3. API interaction through the fetch_data_open_meteo function.
"""

import requests
from weather_service import WeatherServiceError


class OpenMeteoRequestError(WeatherServiceError):
    """Raised when a network or protocol-level error occurs during an API request.

        Attributes:
            error: The underlying requests exception that triggered this error.
    """
    def __init__(self, error: requests.exceptions.HTTPError | requests.exceptions.RequestException):
        """Initializes the error with the original requests exception.

                Args:
                    error: The source HTTPError or RequestException.
        """
        self.error = error

    def __repr__(self):
        """Returns a string representation of the OpenMeteoRequestError instance, including the wrapped error."""
        return f"{self.__class__.__name__}({repr(self.error)})"


class OpenMeteoResponse:
    """A data container for weather information retrieved from OpenMeteo.

        This class serves as a structured representation of the current weather
        conditions and geographical metadata for a specific location.

        Attributes:
            latitude: Geographic latitude coordinate.
            longitude: Geographic longitude coordinate.
            temp_c: Current temperature in degrees Celsius.
            weather_code: OpenMeteo's Unique numeric code for the current weather condition.
    """
    def __init__(self, latitude: float, longitude: float, time: str, temp_c: float, weather_code: int):
        """Initializes an OpenMeteoResponse instance with data from OpenMeteo.

                Args:
                    latitude: The geographic north-south coordinate of the location.
                    longitude: The geographic east-west coordinate of the location.
                    temp_c: The temperature measured in degrees Celsius.
                    weather_code: OpenMeteo's numeric identifier for the current
                        weather condition.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.time = time
        self.temp_c = temp_c
        self.weather_code = weather_code

    def __repr__(self):
        """Returns a string representation of the OpenMeteoResponse instance."""
        return (
            f"OpenMeteoResponse("
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"time={self.time!r}, "
            f"temp_c={self.temp_c!r}, "
            f"weather_code={self.weather_code!r})"
        )


def fetch_data_open_meteo(latitude: float, longitude: float):
    """Fetches real-time weather data from the OpenMeteo service.

        Connects to the OpenMeteo external endpoint using the specified location
        metadata (latitude, longitude) to retrieve current weather conditions
        (such as temperature in Celsius and a weather code) for that location.

        Args:
l           latitude: The North-South geographic coordinate.
            longitude: The East-West geographic coordinate.

        Returns:
            An OpenMeteoResponse object populated with location metadata and current weather conditions.

        Raises:
            OpenMeteoRequestError: If a network error occurs or the API
                returns a non-success status code.
    """
    OPEAN_METEO_ENDPOINT = (f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}"
                            f"&current_weather=true")
    try:
        response = requests.get(OPEAN_METEO_ENDPOINT)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # The response body from Lambda is a JSON string, which we load into a Python dict
        data = response.json()

        latitude = data.get("latitude", None)
        longitude = data.get("longitude", None)

        current_weather_dict = data.get("current_weather", {})
        time = current_weather_dict.get("time", None)
        temperature_c = current_weather_dict.get("temperature", None)
        weather_code = current_weather_dict.get("weathercode", None)

        return OpenMeteoResponse(latitude, longitude, time, temperature_c, weather_code)

    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        raise OpenMeteoRequestError(err)
