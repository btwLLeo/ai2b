# ✅ SETUP COMPLETE - Hybrid Geospatial Retrieval API

## 🎯 What You Got

Your `hybrid_geospatial_retrieval` function is now a **production-ready REST API** that you can call with curl!

---

## 🚀 FASTEST START (3 Steps)

### 1. Double-click to Start Server
```
START_API.bat
```
This will:
- Check Python installation ✅
- Install missing dependencies ✅  
- Start the API server ✅
- Show it's running on http://127.0.0.1:5000

### 2. Open Another Terminal/CMD
And run one of these:

**Simple health check:**
```bash
curl http://127.0.0.1:5000/api/health
```

**Get geospatial data (default):**
```bash
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval
```

**Get geospatial data (1km radius):**
```bash
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=1000"
```

### 3. You Get JSON Back! 🎉

```json
{
  "event": {
    "id": 3651,
    "title": "Attività al Museo dell'aeronautica Gianni Caproni",
    "location": {"lat": 46.020998, "lon": 11.126958}
  },
  "radius_meters": 500,
  "parking": [...],
  "transit": [...]
}
```

---

## 📁 File Guide

| File | Purpose |
|------|---------|
| **START_API.bat** | 🌟 USE THIS - Windows launcher (installs deps + starts server) |
| **api_server.py** | The Flask REST API server |
| **run_server.py** | Python startup script (alternative) |
| **test_api.py** | Automated test suite with curl |
| **README.md** | Full technical documentation |
| **QUICK_START.txt** | Quick reference guide |
| **run_api.bat** | Legacy Windows batch file |
| **start_server.bat** | Legacy Windows batch file |

---

## 🔗 Available Endpoints

### GET /api/health
```bash
curl http://127.0.0.1:5000/api/health
```
Response: `{"status": "ok", "message": "API is running"}`

### GET /api/hybrid_geospatial_retrieval
Search for nearby parking and transit for an event

**Parameters:**
- `event_id` (default: 3651) - Which event to search
- `radius_meters` (default: 500) - Search radius in meters

**Examples:**
```bash
# Default (500m radius)
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval

# 1km radius
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=1000"

# Different event with 2km radius
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=2000"
```

---

## 📊 Sample Data in API

The API comes pre-loaded with Trento data:

**Event:**
- ID: 3651
- Name: Museo dell'aeronautica Gianni Caproni
- Location: 46.020998, 11.126958

**Parking Lots:**
1. Parcheggio Museo Caproni (70m away) - 50 spaces
2. Parcheggio Duomo Trento (5km away) - 120 spaces

**Transit:**
1. Fermata Mattarello / Museo Caproni (130m away) - Lines 7, A

---

## 🧪 Test Your Setup

Run automated tests:
```bash
python test_api.py
```

This will:
- Wait for server
- Test health endpoint
- Test default query
- Test custom radius
- Test error handling

---

## 📈 Response Format

All successful responses return:
```json
{
  "event": {
    "id": <number>,
    "title": "<string>",
    "location": {
      "lat": <float>,
      "lon": <float>
    }
  },
  "radius_meters": <number>,
  "parking": [
    {
      "name": "<string>",
      "stalli": <number>,
      "location": {"lat": <float>, "lon": <float>}
    }
  ],
  "transit": [
    {
      "stop_name": "<string>",
      "lines": ["<string>"],
      "location": {"lat": <float>, "lon": <float>}
    }
  ]
}
```

---

## 🔧 Command-line Tips

### Pretty-print JSON (Windows CMD):
```bash
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval | python -m json.tool
```

### Pretty-print JSON (Windows PowerShell):
```powershell
$response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval"
$response.Content | ConvertFrom-Json | ConvertTo-Json
```

### Pretty-print JSON (Linux/Mac):
```bash
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval | jq
```

### Save response to file:
```bash
curl http://127.0.0.1:5000/api/hybrid_geospatial_retrieval > response.json
```

---

## ⚙️ Troubleshooting

| Problem | Solution |
|---------|----------|
| **Port 5000 in use** | Edit `api_server.py` line 147: change `port=5000` |
| **Flask not found** | Run: `pip install flask` |
| **Connection refused** | Make sure server is running in another terminal |
| **Permission denied** | Make sure START_API.bat is in the right directory |

---

## 🚀 Next Steps

1. ✅ Start server with **START_API.bat**
2. ✅ Test with curl commands
3. ✅ Integrate API URL into your applications
4. ✅ Read README.md for advanced options

---

## 📚 Integration Examples

### Python
```python
import requests
response = requests.get(
    "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval",
    params={"radius_meters": 1000}
)
print(response.json())
```

### JavaScript
```javascript
fetch('http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=1000')
  .then(r => r.json())
  .then(data => console.log(data))
```

### cURL (as shown above)
```bash
curl "http://127.0.0.1:5000/api/hybrid_geospatial_retrieval?radius_meters=1000"
```

---

## ✨ Key Features

✅ RESTful JSON API
✅ Query parameters support  
✅ Error handling
✅ Health check
✅ Auto dependency installation
✅ Cross-platform (Windows/Mac/Linux)
✅ Easy integration
✅ Production-ready with Flask

---

## 📞 Support

- See **README.md** for full documentation
- See **QUICK_START.txt** for command reference
- Check **api_server.py** to understand the code

---

**Status: 🟢 READY TO USE!**

Just run `START_API.bat` and start making curl requests! 🎉
