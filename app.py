from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import requests
import io
import math
import os
import json
import logging
from datetime import datetime, date
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Custom JSON encoder to handle problematic data types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)  # Convert anything else to string

app.json_encoder = CustomJSONEncoder

# Add a health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Health check endpoint accessed")
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/api/data', methods=['GET'])
def get_data():
    # Log received request with parameters
    file_url = request.args.get('url', 'No URL provided')
    page = request.args.get('page', '1')
    rows_per_page = request.args.get('rows_per_page', '100')
    
    # Mask part of the URL for privacy in logs if needed
    safe_url = file_url
    if len(file_url) > 30:
        safe_url = f"{file_url[:15]}...{file_url[-15:]}"
    
    logger.info(f"Received request: URL={safe_url}, page={page}, rows_per_page={rows_per_page}")
    
    # Get parameters from request
    file_url = request.args.get('url')
    
    # Fix: Convert page and rows_per_page to integers with proper error handling
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        error_msg = "Page parameter must be a valid integer"
        logger.error(f"Error: {error_msg}")
        return jsonify({"error": error_msg}), 400
        
    try:
        # Default to 100 rows per page
        rows_per_page = int(request.args.get('rows_per_page', 100))
        
        # Enforce upper limit of 5000 rows per page
        MAX_ROWS_PER_PAGE = 5000
        if rows_per_page > MAX_ROWS_PER_PAGE:
            logger.warning(f"Requested rows_per_page ({rows_per_page}) exceeds maximum allowed ({MAX_ROWS_PER_PAGE}). Using maximum value.")
            rows_per_page = MAX_ROWS_PER_PAGE
    except ValueError:
        error_msg = "Rows per page parameter must be a valid integer"
        logger.error(f"Error: {error_msg}")
        return jsonify({"error": error_msg}), 400
    
    if not file_url:
        error_msg = "URL parameter is required"
        logger.error(f"Error: {error_msg}")
        return jsonify({"error": error_msg}), 400
    
    try:
        # Download the file from the URL
        logger.info(f"Downloading file from URL: {safe_url}")
        response = requests.get(file_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        logger.info(f"File downloaded successfully, status_code={response.status_code}")
        
        # Determine file type from URL
        file_extension = file_url.split('.')[-1].lower()
        logger.info(f"Detected file extension: {file_extension}")
        
        # Read the file into a pandas DataFrame
        if file_extension == 'csv':
            df = pd.read_csv(io.StringIO(response.text))
            logger.info(f"Parsed CSV file: {len(df)} rows, {len(df.columns)} columns")
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(io.BytesIO(response.content))
            logger.info(f"Parsed Excel file: {len(df)} rows, {len(df.columns)} columns")
        else:
            error_msg = "Unsupported file format. Only .xlsx, .xls, and .csv are supported"
            logger.error(f"Error: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        # Handle NaN values and convert problematic data types
        df = df.replace({np.nan: None})
        logger.info("Replaced NaN values with None")
        
        # Calculate pagination
        total_rows = len(df)
        total_pages = math.ceil(total_rows / rows_per_page)
        logger.info(f"Pagination: total_rows={total_rows}, total_pages={total_pages}")
        
        # Validate page number
        if page < 1 or (total_rows > 0 and page > total_pages):
            error_msg = f"Invalid page number. Valid range: 1-{total_pages}"
            logger.error(f"Error: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        # Get the requested page of data
        start_idx = (page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        page_data = df.iloc[start_idx:end_idx]
        logger.info(f"Retrieved page {page}: rows {start_idx}-{end_idx}")
        
        # Convert to list of dictionaries with safer approach
        try:
            # Use pandas json conversion with date handling, then back to Python objects
            json_str = page_data.to_json(orient='records', date_format='iso')
            data = json.loads(json_str)
            logger.info("Successfully converted page data to JSON")
        except Exception as e:
            logger.warning(f"Primary JSON conversion failed: {str(e)}, using fallback method")
            # Fallback to manual dictionary creation with explicit string conversion
            data = []
            for _, row in page_data.iterrows():
                row_dict = {}
                for col in page_data.columns:
                    row_dict[str(col)] = str(row[col]) if row[col] is not None else None
                data.append(row_dict)
            logger.info("Successfully converted page data to JSON using fallback method")
            
        # Add pushDate field to every row
        current_date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Adding pushDate={current_date} to each row")
        for row in data:
            row['pushDate'] = current_date
        
        # Prepare response
        response_data = {
            "data": data,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_rows": total_rows,
                "rows_per_page": rows_per_page
            }
        }
        
        # Manually convert to JSON to handle any edge cases
        try:
            logger.info(f"Finished processing request successfully. Returning {len(data)} rows for page {page}")
            return app.response_class(
                response=json.dumps(response_data, cls=CustomJSONEncoder),
                status=200,
                mimetype='application/json'
            )
        except Exception as json_error:
            error_msg = f"JSON serialization error: {str(json_error)}"
            logger.error(error_msg)
            # Last resort fallback
            return jsonify({"error": "Could not serialize response data", 
                           "details": str(json_error)}), 500
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error fetching file: {str(e)}"
        logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Unhandled exception: {str(e)}\n{error_details}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 