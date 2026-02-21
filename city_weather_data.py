"""City Weather Data Aggregation and Normalization Module.

This module provides the core business logic for the Weather Aggregator. It
is responsible for fetching data from multiple providers, normalizing disparate
API responses into a unified format, and creating a standardized, averaged city weather data
object while filtering out stale or invalid information.

Main components:
    - WeatherCondition: Unified enum for cross-provider weather states.
    - CityWeatherData: The primary data model for aggregated results.
    - Data Processing: Functions for text-to-enum mapping and multi-source averaging.
"""

import csv
import json
from datetime import datetime, timezone
import time
from enum import Enum
from typing import Any, List, Optional
import open_meteo
import utils
from open_meteo import OpenMeteoRequestError, OpenMeteoResponse
import weather_api
from weather_api import WeatherApiRequestError, WeatherApiCityNotFoundError, WeatherApiResponse
from weather_service import WeatherServiceError


class WeatherCondition(Enum):
    """Enumeration of normalized weather condition states used across the application.

        Each member contains a tuple of (id, display_name) to allow for
        consistent UI rendering and internal logic.
    """
    CLEAR = (0, "Clear")
    PARTIALLY_CLOUDY = (1, "Partially Cloudy")
    CLOUDY = (2, "Cloudy")
    DRIZZLE = (3, "Drizzle")
    LIGHT_RAIN = (4, "Light Rain")
    MODERATE_RAIN = (5, "Moderate Rain")
    HEAVY_RAIN = (6, "Heavy Rain")
    LIGHT_SNOW = (7, "Light Snow")
    MODERATE_SNOW = (8, "Moderate Snow")
    HEAVY_SNOW = (9, "Heavy Snow")
    OVERCAST = (10, "Overcast")
    MIST = (11, "Mist")
    FOG = (12, "Fog")
    UNRECOGNIZED = (13, "Unrecognized")


class CityWeatherData:
    """A unified data model representing aggregated weather data for a specific city.

        Attributes:
            latitude: City's geographic north-south coordinate.
            longitude: City's geographic east-west coordinate.
            last_update_epoch: The most recent valid data point's Unix timestamp.
            temp_c: The calculated average temperature in Celsius.
            weather_condition: A list of unique weather conditions reported by the service providers.
    """
    def __init__(self, latitude: float, longitude: float, last_update_epoch: int, temp_c: float,
                 weather_condition: WeatherCondition | List[WeatherCondition]):
        """Initializes CityWeatherData and normalizes weather_condition into a list.

            Args:
                latitude: City's geographic latitude.
                longitude: City's geographic longitude.
                last_update_epoch: Unix epoch timestamp.
                temp_c: Temperature in Celsius.
                weather_condition: A single WeatherCondition or a list of them.
        """
        self.latitude = latitude
        self.longitude = longitude
        self.last_update_epoch = last_update_epoch
        self.temp_c = temp_c
        self.weather_condition = weather_condition \
            if type(weather_condition) is list else [weather_condition]

    def __repr__(self):
        """Returns a string representation of the CityWeatherData instance."""
        return (
            f"{self.__class__.__name__}("
            f"latitude={self.latitude!r}, "
            f"longitude={self.longitude!r}, "
            f"last_update_epoch={self.last_update_epoch!r}, "
            f"temp_c={self.temp_c!r}, "
            f"weather_condition={self.weather_condition!r})"
        )

    def to_json(self):
        """Serializes the object state into a JSON-formatted string.

            Transforms internal attributes into a consumer-ready format, including
            ISO 8601 timestamps, rounded temperatures, and human-readable
            descriptions of weather conditions.

            Returns:
                str: A JSON string containing the processed weather data.
        """
        return json.dumps({
            "latitude": self.latitude,
            "longitude": self.longitude,
            "last_update": utils.epoch_timestamp_to_iso_format(self.last_update_epoch),
            "temp_c": f"{self.temp_c:.2f}" if self.temp_c is not None else "N / A",
            "weather_condition": " or ".join(wc.value[1] for wc in self.weather_condition)
            if len(self.weather_condition) > 0
            else "N / A"
        })


class CityWeatherDataFetchError(Exception):
    """Base exception for errors occurring during the city data fetch process."""
    pass


class CityWeatherDataCityNotFoundError(CityWeatherDataFetchError):
    """Raised when the specified city cannot be resolved by the primary service provider."""
    def __repr__(self):
        """Returns a string representation of the CityWeatherDataCityNotFoundError instance."""
        return f"{self.__class__.__name__}()"


class CityWeatherDataRequestError(CityWeatherDataFetchError):
    """Raised when a network or protocol-level error occurred during an API request of the primary service provider.

        Attributes:
            weather_service_error: The original WeatherServiceError instance.
    """
    def __init__(self, weather_service_error: WeatherServiceError):
        self.weather_service_error = weather_service_error

    """Returns a string representation of the CityWeatherDataRequestError instance."""
    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.weather_service_error)})"


STALE_CUTOFF_NUM_SECONDS = 6 * 60 * 60


def convert_weather_condition_text_to_weather_condition(weather_condition_text: str) -> WeatherCondition:
    """Normalizes raw weather description strings into a standard WeatherCondition enum.

        This function performs 'fuzzy' text matching by stripping common API modifiers
        (e.g., 'at times', 'slight', 'patchy') and mapping the core keywords to an
        internal, provider-agnostic WeatherCondition representation.

        Args:
            weather_condition_text: The raw condition string from a weather service.

        Returns:
            A WeatherCondition enum member. Defaults to UNRECOGNIZED if no match is found.
    """
    clear_weather_condition_text = (weather_condition_text.lower().replace("shower", "")
                              .replace("at times", "")
                              .replace("slight", "light")
                              .replace("fall", "")
                              .replace("partly", "partially")
                              .replace("patchy", "light")
                              .replace("violent", "heavy")
                              .strip())

    if "clear" in clear_weather_condition_text or "sunny" in clear_weather_condition_text:
        return WeatherCondition.CLEAR
    elif "cloudy" in clear_weather_condition_text:
        if "partially" in clear_weather_condition_text:
            return WeatherCondition.PARTIALLY_CLOUDY
        else:
            return WeatherCondition.CLOUDY
    elif "drizzle" in clear_weather_condition_text:
        return WeatherCondition.DRIZZLE
    elif "rain" in clear_weather_condition_text:
        if "light" in clear_weather_condition_text:
            return WeatherCondition.LIGHT_RAIN
        elif "moderate" in clear_weather_condition_text:
            return WeatherCondition.MODERATE_RAIN
        elif "heavy" in clear_weather_condition_text:
            return WeatherCondition.HEAVY_RAIN
        else:
            return WeatherCondition.MODERATE_RAIN
    elif "snow" in clear_weather_condition_text:
        if "light" in clear_weather_condition_text:
            return WeatherCondition.LIGHT_SNOW
        elif "moderate" in clear_weather_condition_text:
            return WeatherCondition.MODERATE_SNOW
        elif "heavy" in clear_weather_condition_text:
            return WeatherCondition.HEAVY_SNOW
        else:
            return WeatherCondition.MODERATE_SNOW
    elif "mist" in clear_weather_condition_text:
        return WeatherCondition.MIST
    elif "fog" in clear_weather_condition_text:
        return WeatherCondition.FOG
    elif "overcast" in clear_weather_condition_text:
        return WeatherCondition.OVERCAST
    else:
        return WeatherCondition.UNRECOGNIZED


def convert_weather_service_response_to_weather_data(weather_service_response: Any) -> CityWeatherData:
    """Transforms provider-specific response object into a unified CityWeatherData format.

        Supports WeatherApiResponse (WeatherAPI) and OpenMeteoResponse (OpenMeteo).
        For OpenMeteo, it performs an additional lookup against a local CSV file
        to map numeric WMO weather codes to human-readable text before normalization.

        Args:
            weather_service_response: An instance of WeatherApiResponse or OpenMeteoResponse.

        Returns:
            A normalized CityWeatherData object.

        Raises:
            ValueError: If the response type is not recognized.
    """
    OPEN_METEO_WEATHER_CODES_FILENAME = "open_meteo_weather_codes.csv"
    weather_condition_text = None

    if type(weather_service_response) is WeatherApiResponse:
        last_update_epoch = weather_service_response.last_update_epoch
        weather_condition_text = weather_service_response.condition_text
    elif type(weather_service_response) is OpenMeteoResponse:
        last_update_epoch = int(datetime.strptime(weather_service_response.time, "%Y-%m-%dT%H:%M")
                                .replace(tzinfo=timezone.utc).timestamp()) \
                            if weather_service_response.time \
                            else None

        try:
            with open(OPEN_METEO_WEATHER_CODES_FILENAME, newline="") as f:
                weather_dict = {int(row["code"]): row["description"] for row in csv.DictReader(f)}
                if weather_service_response.weather_code in weather_dict:
                    weather_condition_text = weather_dict[weather_service_response.weather_code]
                else:
                    print(f"Weather code received in OpenMeteo response not in {OPEN_METEO_WEATHER_CODES_FILENAME}")

        except IOError as e:
            print(f"Could not read open meteo weather codes file: {e}")

    else:
        raise ValueError(f"weather_service_response must be an instance of {WeatherApiResponse.__class__.__name__}"
                         f" or {OpenMeteoResponse.__class__.__name__}")

    latitude = weather_service_response.latitude
    longitude = weather_service_response.longitude
    temp_c = weather_service_response.temp_c
    weather_condition = convert_weather_condition_text_to_weather_condition(weather_condition_text) \
        if weather_condition_text else WeatherCondition.UNRECOGNIZED

    return CityWeatherData(latitude, longitude, last_update_epoch, temp_c, weather_condition)


def average_city_weather_data(weather_data_list: List[CityWeatherData]) -> Optional[CityWeatherData]:
    """Aggregates multiple normalized weather data points into a single unified average report.

        The function applies a filter based firstly on 'freshness' defined by STALE_CUTOFF_NUM_SECONDS
        and secondly by the existence of location metadata and a timestamp.
        Among data points for which the existence condition holds,
        It calculates the mean temperature and identifies the set of unique weather
        conditions across all non-stale data points.

        Args:
            weather_data_list: A list of normalized CityWeatherData objects.

        Returns:
            An aggregated CityWeatherData object, or None if no data point passes the
            existence and freshness filters.
    """
    def city_weather_data_filter(city_weather_data: CityWeatherData) -> bool:
        return (city_weather_data.latitude is not None and city_weather_data.longitude is not None
                and city_weather_data.last_update_epoch is not None
                and time.time() - city_weather_data.last_update_epoch <= STALE_CUTOFF_NUM_SECONDS)

    filtered_weather_data_list = list(filter(city_weather_data_filter, weather_data_list))

    if len(filtered_weather_data_list) == 0:
        return None

    avg_last_update_epoch = min(filtered_weather_data_list, key=lambda data: data.last_update_epoch).last_update_epoch
    filtered_temp_c = [data.temp_c for data in filtered_weather_data_list if data.temp_c is not None]
    avg_temp_c = sum(filtered_temp_c) / len(filtered_temp_c) if len(filtered_temp_c) > 0 else None
    avg_weather_condition = list(set(data.weather_condition[0]
                                        for data in filtered_weather_data_list
                                        if data.weather_condition is not None
                                        and data.weather_condition != [WeatherCondition.UNRECOGNIZED]))

    return CityWeatherData(filtered_weather_data_list[0].latitude, filtered_weather_data_list[0].longitude,
                           avg_last_update_epoch, avg_temp_c, avg_weather_condition)


def fetch_city_weather_data(city_name: str) -> CityWeatherData:
    """Orchestrates multi-source weather data retrieval and aggregation for a city.

        Flow:
            1. Query WeatherAPI by city name (Primary).
            2. Use coordinates from the primary result to query OpenMeteo (Backup).
            3. Normalize both responses into CityWeatherData objects.
            4. Average the data and apply data integrity and stale-data filtering.

        Args:
            city_name: The name of the city to query.

        Returns:
            A final, aggregated CityWeatherData object.

        Raises:
            CityWeatherDataCityNotFoundError: If the city cannot be found.
            CityWeatherDataRequestError: If the primary service request fails.
            CityWeatherDataFetchError: If all retrieved data is considered stale.
    """
    try:
        weather_service_responses = [weather_api.fetch_data_weather_api(city_name)]

        try:
            if weather_service_responses[0].latitude is not None and weather_service_responses[0].longitude is not None:
                weather_service_responses.append(open_meteo.fetch_data_open_meteo(weather_service_responses[0].latitude,
                                                                       weather_service_responses[0].longitude))
        except OpenMeteoRequestError as e:
            print(f'Could not fetch weather data from OpenMeteo: {e}')

        weather_data_list = [convert_weather_service_response_to_weather_data(response)
                                             for response in weather_service_responses]
        avg_weather_data = average_city_weather_data(weather_data_list)

        if avg_weather_data is None:
            raise CityWeatherDataFetchError("All city weather datas were filtered out")

        return avg_weather_data
    except WeatherApiCityNotFoundError:
        raise CityWeatherDataCityNotFoundError()
    except WeatherApiRequestError as e:
        raise CityWeatherDataRequestError(e)
