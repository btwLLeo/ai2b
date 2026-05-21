# Hybrid Geospatial Retrieval API

This API exposes the `hybrid_geospatial_retrieval` function as an HTTP endpoint, allowing you to query it using `curl` or any HTTP client.

## 📦 Dependencies

Make sure you have the required packages installed:
```bash
pip install flask numpy qdrant-client
```

## 🚀 Starting the Server

### Option 1: Using Python (Recommended)
```bash
python run_server.py
```

This will:
- Check for Flask installation
- Install Flask if needed
- Display example curl commands
- Start the API server

### Option 2: Direct Python
```bash
python api_server.py
```

The server will start on `http://127.0.0.1:5000`

## 📝 API Endpoints

### 1. Health Check
Check if the API is running:
```bash
curl http://127.0.0.1:5000/api/health
```

**Response:**
```json
{"status": "ok", "message": "API is running"}
```

### 2. Hybrid Geospatial Retrieval (Default Parameters)
Find nearby parking and transit for event with ID 3651 within 500 meters:
```bash
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval
```

### 3. Hybrid Geospatial Retrieval (Custom Parameters)
Customize the search with query parameters:

**Parameters:**
- `event_id` (integer): The ID of the event to search for (default: 3651)
- `radius_meters` (integer): Search radius in meters (default: 500)

**Example with 1km radius:**
```bash
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=1000"
```

**Response Example:**
```json
{
  "event": {
    "id": 3651,
    "title": "Attività al Museo dell'aeronautica Gianni Caproni",
    "location": {
      "lat": 46.020998,
      "lon": 11.126958
    }
  },
  "radius_meters": 500,
  "parking": [
    {
      "name": "Parcheggio Museo Caproni (Vicinissimo)",
      "stalli": 50,
      "location": {
        "lat": 46.0215,
        "lon": 11.1272
      }
    }
  ],
  "transit": [
    {
      "stop_name": "Fermata Mattarello / Museo Caproni",
      "lines": ["7", "A"],
      "location": {
        "lat": 46.0220,
        "lon": 11.1260
      }
    }
  ]
}
```

## 🧪 Testing

Run the automated test suite:
```bash
python test_api.py
```

This will:
1. Wait for the server to start
2. Run health check
3. Test default parameters
4. Test custom radius parameter
5. Test error handling with non-existent event

## 🔧 Advanced Usage

### Using cURL with Pretty-Printed JSON (on Windows):
```bash
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval | python -m json.tool
```

### Using PowerShell:
```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=500" | ConvertTo-Json
```

### Using Python requests:
```python
import requests

response = requests.get(
    "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval",
    params={"event_id": 3651, "radius_meters": 500}
)
print(response.json())
```

## 📊 Sample Data

The API comes pre-populated with Trento events:
- **Event:** Museo dell'aeronautica Gianni Caproni (ID: 3651)
  - Location: 46.020998, 11.126958
- **Parking:** 2 sample parking lots
  - Parcheggio Museo Caproni (70m away)
  - Parcheggio Duomo Trento (5km away)
- **Transit:** 1 bus stop
  - Fermata Mattarello / Museo Caproni (130m away)

## 🛠️ File Structure

```
dati_eventi/
├── api_server.py          # Main Flask API server
├── run_server.py          # Convenience startup script
├── test_api.py            # Automated test suite
├── run_api.bat            # Windows batch file for starting server
├── start_server.bat       # Windows batch file with Flask check
├── qdrant.py              # Original Qdrant database code
├── pulizia.py             # Data cleaning utilities
├── eventi_trento_puliti.json  # Sample event data
└── README.md              # This file
```

## 🐛 Troubleshooting

### Flask not found
```bash
pip install flask
```

### Port 5000 already in use
Edit `api_server.py` and change the port:
```python
app.run(debug=True, host='127.0.0.1', port=5001)
```

### Connection refused
Make sure the server is running and listening on port 5000:
```bash
netstat -an | findstr 5000  # Windows
lsof -i :5000              # Mac/Linux
```

## 📄 API Response Status Codes

- **200 OK**: Successfully retrieved results
- **404 Not Found**: Event ID doesn't exist
- **500 Internal Server Error**: Server error occurred

## 🔗 Integration

The API is stateless and RESTful, making it easy to integrate with:
- Frontend applications (JavaScript fetch/axios)
- Mobile apps
- Desktop applications
- Command-line tools
- CI/CD pipelines

Enjoy! 🎉
