# ExcelToJSON API

A lightweight API service that converts Excel and CSV files to paginated JSON data.

## Overview

ExcelToJSON is a RESTful API that fetches spreadsheet files from URLs, processes them, and returns the data in a clean, paginated JSON format. It's designed for no-code developers who need to integrate spreadsheet data into web applications without dealing with complex file parsing.

**Live API URL**: [https://exceltojson-pg34.onrender.com](https://exceltojson-pg34.onrender.com)

## Features

- Convert Excel (.xlsx, .xls) and CSV files to JSON
- Support for paginated responses
- Automatic data type handling and conversion
- Cross-origin resource sharing (CORS) enabled
- Logging of requests and processing steps
- Timestamps added to data with pushDate field
- Health check endpoint for monitoring

## API Documentation

### Health Check

**Endpoint**: `GET /health`

Verifies the service is running correctly.

**Example**: [https://exceltojson-pg34.onrender.com/health](https://exceltojson-pg34.onrender.com/health)

**Response**:
```json
{
  "status": "ok",
  "message": "Service is running"
}
```

### Convert Spreadsheet to JSON

**Endpoint**: `GET /api/data`

**Query Parameters**:

| Parameter | Type | Required | Description | Default | Constraints |
|-----------|------|----------|-------------|---------|-------------|
| url | string | Yes | URL to an Excel or CSV file | - | Must be accessible |
| page | integer | No | Page number to return | 1 | Must be ≥ 1 |
| rows_per_page | integer | No | Number of rows per page | 100 | Maximum 5000 |

**Example**: [https://exceltojson-pg34.onrender.com/api/data?url=https://example.com/data.xlsx&page=1&rows_per_page=100](https://exceltojson-pg34.onrender.com/api/data?url=https://example.com/data.xlsx&page=1&rows_per_page=100)

**Success Response (200 OK)**:
```json
{
  "data": [
    {
      "column1": "value1",
      "column2": "value2",
      ...
      "pushDate": "2023-11-15"
    },
    ...
  ],
  "pagination": {
    "current_page": 1,
    "total_pages": 10,
    "total_rows": 1000,
    "rows_per_page": 100
  }
}
```

**Error Responses**:

| Status Code | Description | Example Response |
|-------------|-------------|------------------|
| 400 | Bad Request | `{"error": "URL parameter is required"}` |
| 400 | Bad Request | `{"error": "Page parameter must be a valid integer"}` |
| 400 | Bad Request | `{"error": "Unsupported file format. Only .xlsx, .xls, and .csv are supported"}` |
| 500 | Server Error | `{"error": "Could not serialize response data", "details": "..."}` |

## Setup and Deployment

### Prerequisites

- Docker
- Git

### Local Development

```bash
# Clone the repository
git clone https://github.com/evanfurniss-dev/ExcelToJSON.git
cd ExcelToJSON

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Docker Deployment

```bash
# Build the Docker image
docker build -t exceltojson .

# Run the container
docker run -p 8080:8080 exceltojson
```

### Cloud Deployment

The service is currently deployed at [https://exceltojson-pg34.onrender.com](https://exceltojson-pg34.onrender.com) using Render.

You can deploy your own instance to various cloud providers:

- **Render**: Connect your GitHub repository to Render for automatic deployments
- **DigitalOcean App Platform**: Recommended for consistent workloads ($5/month)
- **Google Cloud Run**: Good for variable workloads (pay-per-use)
- **Google Compute Engine**: Recommended for steady, frequent usage (e2-micro ~$6-8/month)

## Configuration

### Environment Variables

- `PORT`: The port on which the service runs (default: 8080)

### Gunicorn Configuration

The `gunicorn_config.py` file contains settings for the production server:

- `workers`: Number of worker processes (default: 4)
- `threads`: Threads per worker (default: 2)
- `timeout`: Request timeout in seconds (default: 120)

## Technical Details

### Data Processing Flow

1. Request validation
2. File download from URL
3. File type detection and parsing with pandas
4. Data cleaning (NaN values → null)
5. Pagination calculation
6. JSON conversion with data type handling
7. Addition of pushDate timestamp
8. Response formation

### Memory Considerations

The API loads the entire file into memory, so resource usage scales with file size:
- Small files (1,000 rows): ~5MB memory
- Medium files (100,000 rows): ~500MB memory
- Large files (1,000,000+ rows): 5GB+ memory (not recommended)

To mitigate memory issues, a limit of 5000 rows per page is enforced.

## Limitations

- Entire source file is loaded into memory
- No caching mechanism (files are re-processed on each request)
- Limited to Excel and CSV formats
- No built-in authentication
- Maximum 5000 rows per page

## Example Usage

### JavaScript Fetch

```javascript
// Fetch the first page with 100 rows per page
fetch('https://exceltojson-pg34.onrender.com/api/data?url=https://example.com/data.xlsx&page=1&rows_per_page=100')
  .then(response => response.json())
  .then(data => {
    console.log(`Loaded ${data.pagination.total_rows} total rows`);
    console.log(`Page ${data.pagination.current_page} of ${data.pagination.total_pages}`);
    console.log(data.data); // Array of rows
  })
  .catch(error => console.error('Error:', error));
```

### Python Requests

```python
import requests

response = requests.get(
    'https://exceltojson-pg34.onrender.com/api/data',
    params={
        'url': 'https://example.com/data.csv',
        'page': 1,
        'rows_per_page': 100
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"Loaded {data['pagination']['total_rows']} total rows")
    print(f"Page {data['pagination']['current_page']} of {data['pagination']['total_pages']}")
    for row in data['data']:
        print(row)
else:
    print(f"Error: {response.json()['error']}")
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
