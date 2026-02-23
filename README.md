# Weather Aggregator

A serverless AWS Lambda function that aggregates real-time weather data from multiple REST APIs (currently only open-meteo.com and weatherapi.com are supported), returns a normalized JSON response, and stores ip-based user history in DynamoDB.

## Usage

The service is deployed as an AWS Lambda Function URL. You can consume the API using any standard HTTP client.

### 1. Simple cURL Request

```bash
curl "https://vt7rupl6qklrnz4z6w2acoo22u0mzgdi.lambda-url.eu-north-1.on.aws?city=New York"
```

### 2. Python Client
This is the recommended way to interact with the service programmatically. It handles URL encoding for city names and parses the JSON response.

```python
import requests
import json

API_ENDPOINT = "https://ehftqv7cnzsgir5o2w2aebp5ji0haqbr.lambda-url.eu-north-1.on.aws/"


def fetch_data_from_api():
    try:
        response = requests.get(API_ENDPOINT, params={"city": "New York"})
        response.raise_for_status()
        data = response.json()

        print("✅ API Call Successful!")
        print("Status Code:", response.status_code)
        print("Response Data (Python dict):")
        print(json.dumps(data, indent=4))

    except requests.exceptions.HTTPError as err:
        print("❌ HTTP Error occurred")
        print("Status Code:", err.response.status_code)
        print("Content:", err.response.content)
    except requests.exceptions.RequestException as err:
        print(f"❌ An error occurred during the request: {err}")


if __name__ == "__main__":
    fetch_data_from_api()
```
