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
    assert convert_weather_condition_text_to_weather_condition(weather_condition_text) == expected_output


def test_average_city_weather_filters_stale_data():
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
    # testing an invalid weather condition text
    result = convert_weather_condition_text_to_weather_condition("Apocalyptic Meteor Shower")
    assert result == WeatherCondition.UNRECOGNIZED
