"""Unit tests for city weather data processing and normalization.

This module validates the core business logic of the weather aggregator,
including the mapping of raw API textual weather descriptions to internal
enumerations and the time-based filtering of stale weather reports.

The tests ensure that data aggregation remains accurate by discarding
outdated information and handling unrecognized weather strings gracefully.
"""

import pytest
from city_weather_data import (
    convert_weather_condition_text_to_weather_condition,
    average_city_weather_data,
    WeatherCondition,
    CityWeatherData,
    STALE_CUTOFF_NUM_SECONDS
)


@pytest.mark.parametrize("weather_condition_text, expected_output", [
    ("rain", WeatherCondition.MODERATE_RAIN),
    ("heavy rain", WeatherCondition.HEAVY_RAIN),
    ("violent rain", WeatherCondition.HEAVY_RAIN),
    ("Partly shower cloudy", WeatherCondition.PARTIALLY_CLOUDY),
    ("sunny", WeatherCondition.CLEAR),
    ("mist", WeatherCondition.MIST),
])
def test_weather_mappings(weather_condition_text, expected_output):
    """Verifies that various API weather condition text strings map correctly to WeatherCondition enums.

        This test uses parameterization to check multiple "fuzzy" text matches,
        ensuring the mapping logic is robust against different API naming conventions.
    """
    assert convert_weather_condition_text_to_weather_condition(weather_condition_text) == expected_output


def test_average_city_weather_filters_stale_data():
    """Validates that stale data points are excluded from the averaging logic.

        The test creates two data points: one older than STALE_CUTOFF_NUM_SECONDS
        and one within the limit. It asserts that the resulting average ignores
        the stale value entirely.
    """
    import time
    now = time.time()
    stale_time = int(now) - (STALE_CUTOFF_NUM_SECONDS + 100)  # stale
    fresh_time = int(now) - (STALE_CUTOFF_NUM_SECONDS - 100)  # fresh

    data1 = CityWeatherData(32.0, 34.0, stale_time, 20.0, WeatherCondition.CLEAR)
    data2 = CityWeatherData(32.0, 34.0, fresh_time, 30.0, WeatherCondition.CLEAR)

    result = average_city_weather_data([data1, data2])

    # result should only consider data2, so temp should be 30.0, not the average (25.0)
    assert result.temp_c == 30.0
    assert result.last_update_epoch == fresh_time


def test_weather_mapping_unrecognized():
    """Ensures that unknown textual weather descriptions default to the UNRECOGNIZED WeatherCondition enumeration.

        This acts as a safety catch for when an external API introduces a new
        weather condition string that hasn't been mapped yet or when the weather condition string is invalid.
    """
    # testing an invalid weather condition text
    result = convert_weather_condition_text_to_weather_condition("Apocalyptic Meteor Shower")
    assert result == WeatherCondition.UNRECOGNIZED
