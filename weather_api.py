"""WeatherAPI Service Provider Module.

This module implements the integration with the WeatherAPI.com service.
It provides functional utilities for fetching real-time weather data,
structured data models for internal consumption, and a specialized
exception hierarchy to handle API-specific failure modes.

The module follows a clean separation of concerns:
    1. Exception handling for network and logic errors.
    2. Data modeling via the WeatherApiResponse class.
    3. API interaction through the fetch_data_weather_api function.
"""

import json
import os

import requests
from weather_service import WeatherServiceError


class WeatherApiError(WeatherServiceError):
    """Base exception for errors originating from the WeatherAPI service."""
    pass


class WeatherApiCityNotFoundError(WeatherApiError):
    """Raised when the requested city cannot be found in the WeatherAPI database."""
    pass


class WeatherApiRequestError(WeatherApiError):
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
        """Returns a string representation of the WeatherApiRequestError instance, including the wrapped error."""
        return f"{self.__class__.__name__}({repr(self.error)})"


class WeatherApiResponse:
    """A data container for weather information retrieved from WeatherAPI.

        This class serves as a structured representation of the current weather
        conditions and geographical metadata for a specific location.

        Attributes:
            city_name: Name of the city (e.g., 'London').
            country_name: Name of the country.
            latitude: Geographic latitude coordinate.
            longitude: Geographic longitude coordinate.
            last_update_epoch: The time of the last weather update (on WeatherApi's end) in Unix epoch format.
            temp_c: Current temperature in degrees Celsius.
            condition_text: Human-readable weather description (e.g., 'Partly cloudy').
            condition_code: WeatherApi's Unique numeric code for the current weather condition.
    """

    # class WeatherCondition(Enum):
    #     SUNNY = (1000, "Sunny")
    #     PARTIALLY_CLOUDY = (1003, "Partially Cloudy")
    #     CLOUDY = (1006, "Cloudy")
    #     OVERCAST = (1009, "Overcast")
    #     MIST = (1030, "Mist"),
    #     PATCHY_LIGHT_DRIZZLE = (1150, "Patchy Light Drizzle")
    #     LIGHT_DRIZZLE = (1153, "Light Drizzle")
    #     FREEZING_DRIZZLE = (1168, "Freezing Drizzle")
    #     HEAVY_FREEZING_DRIZZLE = (1171, "Heavy Freezing Drizzle")
    #     LIGHT_RAIN = (1183, "Light Rain")
    #     MODERATE_RAIN_AT_TIMES = (1186, "Moderate Rain at Times")
    #     MODERATE_RAIN = (1189, "Moderate Rain")
    #     HEAVY_RAIN_AT_TIMES = (1192, "Heavy rain at Times")
    #     HEAVY_RAIN = (1195, "Heavy rain")
    #     LIGHT_SNOW = (1213, "Light Snow")
    #     PATCHY_MODERATE_SNOW = (1216, "Patchy Moderate Snow")

    def __init__(self, city_name: str, country_name: str,
                 latitude: float, longitude: float, last_update_epoch: int, temp_c: float, condition_text: str,
                 condition_code: int):
        """Initializes a WeatherApiResponse instance with data from WeatherAPI.

                Args:
                    city_name: The name of the city (e.g., 'London').
                    country_name: The name of the country (e.g., 'United Kingdom').
                    latitude: The geographic north-south coordinate of the location.
                    longitude: The geographic east-west coordinate of the location.
                    last_update_epoch: The Unix timestamp (seconds) of the last
                        weather data update.
                    temp_c: The temperature measured in degrees Celsius.
                    condition_text: A human-readable description of the weather
                        (e.g., 'Partly cloudy').
                    condition_code: WeatherApi's numeric identifier for the current
                        weather condition.
        """
        self.city_name = city_name
        self.country_name = country_name
        self.latitude = latitude
        self.longitude = longitude
        self.last_update_epoch = last_update_epoch
        self.temp_c = temp_c
        self.condition_text = condition_text
        self.condition_code = condition_code

    def __repr__(self) -> str:
        """Returns a string representation of the WeatherApiResponse instance."""
        return (
            f"{self.__class__.__name__}("
            f"city_name={self.city_name!r}, "
            f"country_name={self.country_name!r}, "
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"temp_c={self.temp_c!r}, "
            f"condition_text={self.condition_text!r})"
        )


def fetch_data_weather_api(city_name: str) -> WeatherApiResponse:
    """Fetches real-time weather data from the WeatherAPI service.

        Connects to the WeatherAPI external endpoint to retrieve city location
        metadata (i.e. latitude, longitude) and current weather conditions
        (such as temperature in Celsius and a weather description) for a specific city.

        Args:
            city_name: The name of the city to query (e.g., "London" or "Tel Aviv").

        Returns:
            A WeatherApiResponse object populated with location metadata and current weather conditions.

        Raises:
            WeatherApiCityNotFoundError: If the API returns a 1006 error code
                indicating the city was not found.
            WeatherApiRequestError: If a network error occurs or the API
                returns a non-success status code.
    """
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
    WEATHER_API_ENDPOINT = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city_name}"
    try:
        response = requests.get(WEATHER_API_ENDPOINT)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # The response body from Lambda is a JSON string, which we load into a Python dict
        data = response.json()

        location_dict = data.get("location", {})
        city_name = location_dict.get("name")
        country_name = location_dict.get("country")
        latitude = location_dict.get("lat", None)
        longitude = location_dict.get("lon", None)

        current_dict = data.get("current", {})
        last_updated_epoch = current_dict.get("last_updated_epoch", None)
        temp_c = current_dict.get("temp_c", None)

        condition_dict = current_dict.get("condition", {})
        condition_text = condition_dict.get("text", None)
        condition_code = condition_dict.get("code", None)

        return WeatherApiResponse(city_name, country_name, latitude, longitude, last_updated_epoch, temp_c,
                                  condition_text, condition_code)

    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as err:
        if (err.response is not None
            and err.response.content is not None
            and json.loads(err.response.content.decode('utf-8'))
                        .get("error", {}).get("code", -1) == 1006):
            raise WeatherApiCityNotFoundError()
        else:
            raise WeatherApiRequestError(err)
