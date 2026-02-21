"""AWS Lambda Handler and Request Orchestration Module.

This module acts as the entry point for the Weather Aggregator service. It
manages the end-to-end lifecycle of an HTTP request, including:
    1. Extracting parameters and client metadata (IP).
    2. Interacting with DynamoDB to track user access patterns and history.
    3. Coordinating with the business logic layer to fetch city weather data.
    4. Mapping internal outcomes to standard HTTP status codes and responses.

Environment Requirements:
    - DynamoDB Table: 'RequestIPLogs' must exist with 'ip' as the Partition Key.
"""
import json
import boto3
import time
from typing import Optional, List, Tuple, TYPE_CHECKING

# makes AWS specific type hinting available in IDE, without bundling the library when deploying to the cloud
if TYPE_CHECKING:
    from aws_lambda_typing.context import Context

from botocore.exceptions import ClientError

import city_weather_data
import utils
from city_weather_data import CityWeatherDataCityNotFoundError
from city_weather_data import CityWeatherDataRequestError

dynamodb = boto3.resource('dynamodb')
ip_table = dynamodb.Table("RequestIPLogs")


def get_request_ip(event: dict) -> Optional[str]:
    """Extracts the source IP address from the Lambda Proxy integration event."""
    return event.get('requestContext', {}).get('http', {}).get('sourceIp', None)


def get_request_city_param(event: dict) -> Optional[str]:
    """Retrieves the 'city' query string parameter from the incoming request."""
    return event.get('queryStringParameters', {}).get('city', None)


def get_response(status_code: int, context: Context, content_type: str = "application/json", **kwargs) -> dict:
    """Constructs a standardized HTTP response for the Lambda Gateway.

        Args:
            status_code: HTTP status code to return.
            context: AWS Lambda context object (used for Request ID).
            content_type: MIME type for the response header.
            **kwargs: Arbitrary key-value pairs to include in the JSON body.

        Returns:
            A dictionary formatted as an AWS Lambda HTTP response.
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': content_type,
            "X-Request-ID": context.aws_request_id
        },
        'body': json.dumps({
            "requestId": context.aws_request_id,
        } | kwargs)  # add kwargs to body dict
    }


def get_ip_last_accessed_timestamp_from_db(ip) -> Tuple[Optional[int], bool]:
    """Retrieves the most recent access timestamp for a specific IP from DynamoDB.

        Args:
            ip: The client's IP address.

        Returns:
            A tuple containing (timestamp_epoch, success_flag).
    """
    try:
        # Only retrieve the 'LastAccessTimestamp' attribute
        response = ip_table.get_item(Key={'ip': ip},
                                     ProjectionExpression='LastAccessTimestamp')
        last_access_timestamp = response.get('Item', {}).get('LastAccessTimestamp', None)

        return (int(last_access_timestamp) if last_access_timestamp else None), True
    except ClientError as e:
        print(f"Error retrieving LastAccessTimestamp: {e}")
        return None, False


def update_ip_fields_in_db(ip, last_access_timestamp: int, new_city: str) \
        -> Tuple[Optional[int], Optional[List[str]], bool]:
    """Updates the user's audit trail (last_access_timestamp and recent_cities) in DynamoDB.

        Atomically updates the 'LastAccessTimestamp' and appends the requested
        city to the IP's aggregated 'recent_cities' list.

        Returns:
            A tuple containing (updated_timestamp, recent_city_list, success_flag).
    """
    try:
        # 4. Perform the Update
        response = ip_table.update_item(
            Key={
                'ip': ip
            },
            UpdateExpression="SET LastAccessTimestamp = :t,"
                             " recent_cities = list_append(:c, if_not_exists(recent_cities, :empty))",
            ExpressionAttributeValues={
                ':t': last_access_timestamp,
                ':c': [new_city],
                ':empty': []
            },
            ReturnValues="UPDATED_NEW"
        )
        response_attributes = response['Attributes']
        print(f"IP fields Update successful: {response_attributes}")
        return int(response_attributes['LastAccessTimestamp']), response_attributes['recent_cities'], True

    except ClientError as e:
        print(f"LastAccessTimestamp Update failed: {str(e)}")
        return None, None, False


def handle_missing_parameter_city(context: Context) -> dict:
    """Returns a formatted HTTP 400 Bad Request response for missing query parameters."""
    return get_response(400, context, error="Bad Request",
                        message="The required query parameter 'city' is missing.",
                        details="Please include ?city=CityName in the request URL.")


def handle_city_not_found(context: Context, city: str, last_access_timestamp_message: str, recent_cities: List[str]) \
        -> dict:
    """Returns a formatted HTTP 404 Not Found response when a city name cannot be resolved
        by the primary service provider.
    """
    return get_response(404, context, error="Not found", message="No data available for the specified city.",
                        details=f"No matching city was found with the name '{city}'.",
                        last_access=last_access_timestamp_message,
                        recent_cities=recent_cities[1:])


def handle_internal_server_error(context: Context):
    """Returns a formatted HTTP 500 Internal Server Error response for DB access failures."""
    return get_response(500, context, error="Internal Server Error",
                        message="An unexpected error occurred.",
                        details="Please try again later.")


def handle_service_unavailable_error(context: Context, last_access_timestamp_message: str) -> dict:
    """Returns a formatted HTTP 503 Service Unavailable response for service provider timeouts/failures."""
    return get_response(503, context, error="Service Unavailable",
                        message="Service is currently unavailable.",
                        details="Please try again later.",
                        last_access=last_access_timestamp_message)


def lambda_handler(event, context: Context) -> dict:
    """The primary execution entry point for the AWS Lambda function.

        Execution Flow:
            1. Parse and validate query parameters.
            2. Identify client IP and retrieve/update audit trail in DynamoDB.
            3. Invoke business logic to fetch and aggregate city weather data.
            4. Return a JSON structured HTTP response with city weather results and user history,
            or an appropriate error status.
    """

    # update for yml deploy test
    city = get_request_city_param(event)

    if not city:
        print("Request missing 'city' parameter")
        return handle_missing_parameter_city(context)

    request_ip = get_request_ip(event)

    if not request_ip:
        return handle_internal_server_error(context)

    print(f"Received request from IP: {request_ip}")

    prev_last_access_timestamp, success = get_ip_last_accessed_timestamp_from_db(request_ip)

    if not success:
        return handle_internal_server_error(context)

    timestamp_seconds = int(time.time())

    cur_last_access_timestamp, recent_cities, success = update_ip_fields_in_db(request_ip, timestamp_seconds, city)

    if not success:
        return handle_internal_server_error(context)

    prev_last_access_timestamp_message = utils.epoch_timestamp_to_iso_format(prev_last_access_timestamp) \
        if prev_last_access_timestamp else "N / A"

    print(f"Previous last access: {prev_last_access_timestamp_message}")
    print(f"Recent cities: {recent_cities}")

    try:
        weather_data = city_weather_data.fetch_city_weather_data(city)

        return get_response(200, context, city=city, weather=weather_data.to_json(),
                            last_access=prev_last_access_timestamp_message,
                            recent_cities=recent_cities[1:])
    except CityWeatherDataCityNotFoundError as e:
        print(f'City Weather data fetching failed as city was not found: {e}')
        return handle_city_not_found(context, city, prev_last_access_timestamp_message, recent_cities)
    except CityWeatherDataRequestError as e:
        print(f'City Weather data fetching failed due to a request error: {e}')
        return handle_service_unavailable_error(context, prev_last_access_timestamp_message, recent_cities)
