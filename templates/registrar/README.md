# Lago Event Generator

A Python script to periodically send events to the Lago payment system API with configurable parameters.

## Features

- **Configurable Parameters**: Control all key parameters via command line arguments
- **Periodic Execution**: Send events at configurable intervals
- **Error Handling**: Robust error handling with detailed logging
- **Event Properties**: Support for custom event properties
- **Limited Execution**: Option to limit the number of events sent
- **Graceful Shutdown**: Handle Ctrl+C interruption gracefully

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Send events every 60 seconds:

```bash
python event_generator.py \
  --lago_url "https://api.getlago.com" \
  --api_key "your_api_key" \
  --external_subscription_id "sub_123" \
  --event_code "usage" \
  --interval 60
```

### Advanced Usage

Send events with custom properties:

```bash
python event_generator.py \
  --lago_url "https://api.getlago.com" \
  --api_key "your_api_key" \
  --external_subscription_id "sub_123" \
  --event_code "api_call" \
  --interval 30 \
  --properties '{"requests": 1, "endpoint": "/api/v1/users"}'
```

Send a limited number of events:

```bash
python event_generator.py \
  --lago_url "https://api.getlago.com" \
  --api_key "your_api_key" \
  --external_subscription_id "sub_123" \
  --event_code "test" \
  --interval 10 \
  --max_events 5
```

Enable verbose logging:

```bash
python event_generator.py \
  --lago_url "https://api.getlago.com" \
  --api_key "your_api_key" \
  --external_subscription_id "sub_123" \
  --event_code "usage" \
  --interval 60 \
  --verbose
```

## Command Line Arguments

### Required Arguments

- `--lago_url`: Lago API base URL (e.g., https://api.getlago.com)
- `--api_key`: Lago API key for authentication
- `--external_subscription_id`: External subscription ID
- `--event_code`: Event code to send
- `--interval`: Time interval between events in seconds

### Optional Arguments

- `--properties`: JSON string of event properties (e.g., '{"requests": 1, "endpoint": "/api"}')
- `--max_events`: Maximum number of events to send (default: unlimited)
- `--verbose`: Enable verbose logging

## Event Structure

The script sends events in the following format to the Lago API:

```json
{
  "event": {
    "external_subscription_id": "your_subscription_id",
    "code": "your_event_code",
    "properties": {
      "timestamp": "2024-01-01T12:00:00.000Z",
      "custom_property": "value"
    }
  }
}
```

## Logging

The script provides detailed logging including:
- Event sending status
- Error messages with HTTP status codes
- Periodic execution status
- Graceful shutdown messages

## Error Handling

- Network timeouts (30 seconds)
- HTTP error responses
- JSON parsing errors for properties
- Graceful handling of Ctrl+C interruption

## Security Notes

- API keys are passed via command line arguments
- Consider using environment variables for sensitive data in production
- The script uses Bearer token authentication as required by Lago API

## Example Output

```
2024-01-01 12:00:00,000 - __main__ - INFO - Starting periodic event generation. Interval: 60s, Max events: unlimited
2024-01-01 12:00:00,001 - __main__ - INFO - Sending event 'usage' to subscription 'sub_123'
2024-01-01 12:00:00,500 - __main__ - INFO - Event 'usage' sent successfully
2024-01-01 12:00:00,501 - __main__ - INFO - Waiting 60 seconds before next event...
```