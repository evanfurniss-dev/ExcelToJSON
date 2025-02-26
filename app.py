from flask import Flask, request, jsonify
import pandas as pd
import numpy as np
import requests
import io
import math
import os
import json
from datetime import datetime, date
from flask_cors import CORS

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
    return jsonify({"status": "ok", "message": "Service is running"})

@app.route('/api/data', methods=['GET'])
def get_data():
    # Get parameters from request
    file_url = request.args.get('url')
    
    # Fix: Convert page and rows_per_page to integers with proper error handling
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        return jsonify({"error": "Page parameter must be a valid integer"}), 400
        
    try:
        rows_per_page = int(request.args.get('rows_per_page', 10))
    except ValueError:
        return jsonify({"error": "Rows per page parameter must be a valid integer"}), 400
    
    if not file_url:
        return jsonify({"error": "URL parameter is required"}), 400
    
    try:
        # Download the file from the URL
        response = requests.get(file_url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Determine file type from URL
        file_extension = file_url.split('.')[-1].lower()
        
        # Read the file into a pandas DataFrame
        if file_extension == 'csv':
            df = pd.read_csv(io.StringIO(response.text))
        elif file_extension in ['xlsx', 'xls']:
            df = pd.read_excel(io.BytesIO(response.content))
        else:
            return jsonify({"error": "Unsupported file format. Only .xlsx, .xls, and .csv are supported"}), 400
        
        # Handle NaN values and convert problematic data types
        df = df.replace({np.nan: None})
        
        # Calculate pagination
        total_rows = len(df)
        total_pages = math.ceil(total_rows / rows_per_page)
        
        # Validate page number
        if page < 1 or (total_rows > 0 and page > total_pages):
            return jsonify({"error": f"Invalid page number. Valid range: 1-{total_pages}"}), 400
        
        # Get the requested page of data
        start_idx = (page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        page_data = df.iloc[start_idx:end_idx]
        
        # Convert to list of dictionaries with safer approach
        try:
            # Use pandas json conversion with date handling, then back to Python objects
            json_str = page_data.to_json(orient='records', date_format='iso')
            data = json.loads(json_str)
        except Exception as e:
            # Fallback to manual dictionary creation with explicit string conversion
            data = []
            for _, row in page_data.iterrows():
                row_dict = {}
                for col in page_data.columns:
                    row_dict[str(col)] = str(row[col]) if row[col] is not None else None
                data.append(row_dict)
        
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
            return app.response_class(
                response=json.dumps(response_data, cls=CustomJSONEncoder),
                status=200,
                mimetype='application/json'
            )
        except Exception as json_error:
            print(f"JSON serialization error: {str(json_error)}")
            # Last resort fallback
            return jsonify({"error": "Could not serialize response data", 
                           "details": str(json_error)}), 500
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error fetching file: {str(e)}"}), 400
    except Exception as e:
        # Add more detailed error information for debugging
        import traceback
        error_details = traceback.format_exc()
        print(error_details)  # Log the full error
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 