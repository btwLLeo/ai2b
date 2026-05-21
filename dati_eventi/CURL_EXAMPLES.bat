REM ============================================================
REM EXAMPLE CURL COMMANDS - Hybrid Geospatial Retrieval API
REM ============================================================
REM
REM To use these commands:
REM 1. Make sure START_API.bat is running
REM 2. Open a new CMD/PowerShell window
REM 3. Copy-paste any command below
REM
REM ============================================================


REM 🟢 TEST 1: Health Check
curl http://127.0.0.1:5000/api/health


REM 🟢 TEST 2: Default Query (500m radius)
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval


REM 🟢 TEST 3: Extended Radius (1000m)
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=1000"


REM 🟢 TEST 4: Custom Event ID (if you have others)
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651"


REM 🟢 TEST 5: Both Parameters Combined
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=1500"


REM 🟢 TEST 6: Pretty-print JSON output (Windows CMD)
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval | python -m json.tool


REM 🟢 TEST 7: Save response to file
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval > response.json


REM 🟢 TEST 8: With Headers
curl -H "Content-Type: application/json" http://127.0.0.1:5000/api/hybrid_geospatial_retrieval


REM 🟢 TEST 9: Different radius values
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=100"
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=500"
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=2000"
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=5000"


REM 🟢 TEST 10: Non-existent event (error test)
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=99999"


REM ============================================================
REM POWERSHELL EXAMPLES
REM ============================================================

REM Run these in PowerShell instead of CMD:

REM Health check (PowerShell):
REM Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health"

REM API call with pretty JSON (PowerShell):
REM $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval"
REM $response.Content | ConvertFrom-Json | ConvertTo-Json

REM Save response (PowerShell):
REM Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval" -OutFile "response.json"


REM ============================================================
REM PYTHON EXAMPLES
REM ============================================================

REM Run these in Python:

REM import requests
REM response = requests.get('http://127.0.0.1:5000/api/health')
REM print(response.json())

REM import requests
REM response = requests.get(
REM     'http://127.0.0.1:5000/api/hybrid_geospatial_retrieval',
REM     params={'radius_meters': 1000}
REM )
REM print(response.json())


REM ============================================================
REM NOTES
REM ============================================================

REM - Make sure the server is running before executing any curl command
REM - Replace 127.0.0.1 with your server's IP if accessing remotely
REM - Replace 5000 with different port if you changed it in api_server.py
REM - JSON responses are returned for all successful calls
REM - Error responses include error messages in JSON format
REM - radius_meters is in meters (1000 = 1km, 500 = 500m)
REM - event_id must exist in the database (currently only 3651)


REM ============================================================
REM EXPECTED RESPONSE FORMAT
REM ============================================================

REM {
REM   "event": {
REM     "id": 3651,
REM     "title": "Attività al Museo dell'aeronautica Gianni Caproni",
REM     "location": {
REM       "lat": 46.020998,
REM       "lon": 11.126958
REM     }
REM   },
REM   "radius_meters": 500,
REM   "parking": [
REM     {
REM       "name": "Parcheggio Museo Caproni (Vicinissimo)",
REM       "stalli": 50,
REM       "location": {
REM         "lat": 46.0215,
REM         "lon": 11.1272
REM       }
REM     }
REM   ],
REM   "transit": [
REM     {
REM       "stop_name": "Fermata Mattarello / Museo Caproni",
REM       "lines": ["7", "A"],
REM       "location": {
REM         "lat": 46.022,
REM         "lon": 11.126
REM       }
REM     }
REM   ]
REM }
