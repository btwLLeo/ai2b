import os
import json
import math
import numpy as np
from flask import Flask, request, jsonify, render_template
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, Filter, FieldCondition, GeoRadius, PointStruct, VectorParams

app = Flask(__name__)

client = QdrantClient(":memory:")
VECTOR_DIM = 4


# -------------------------
# LOAD DATA
# -------------------------
with open("eventi_trento_puliti.json", "r", encoding="utf-8") as f:
    EVENTS = json.load(f)

with open("trento_bus_stops_with_lines.json", "r", encoding="utf-8") as f:
    BUS_STOPS = json.load(f)

with open("trento_parking.json", "r", encoding="utf-8") as f:
    PARKING = json.load(f)


# -------------------------
# DISTANCE
# -------------------------
def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# -------------------------
# EVENTS -> GEOJSON
# -------------------------
def event_to_feature(event):
    try:
        loc = event.get("metadata", {}).get("location", {})
        lat = float(loc.get("latitude"))
        lon = float(loc.get("longitude"))

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None

        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": {
                "id": event.get("id"),
                "title": event.get("title"),
                "type": "event",
                "url": event.get("metadata", {}).get("url"),
                "start": event.get("metadata", {}).get("schedule", {}).get("next_upcoming_start"),
                "end": event.get("metadata", {}).get("schedule", {}).get("next_upcoming_end"),
            }
        }
    except Exception:
        return None


@app.route("/api/map_data")
def map_data():
    features = []
    for e in EVENTS:
        f = event_to_feature(e)
        if f:
            features.append(f)

    return jsonify({
        "type": "FeatureCollection",
        "features": features
    })


# -------------------------
# BUS STOPS
# -------------------------
@app.route("/api/nearby_bus_stops")
def nearby_bus_stops():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        radius = float(request.args.get("radius", 500))

        results = []

        for stop in BUS_STOPS:
            try:
                slat = float(stop["lat"])
                slon = float(stop["lon"])

                d = distance_m(lat, lon, slat, slon)

                if d <= radius:
                    results.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [slon, slat]
                        },
                        "properties": {
                            "name": stop.get("name"),
                            "distance": round(d),
                            "lines": stop.get("lines", []),
                            "type": "bus_stop"
                        }
                    })
            except Exception:
                continue

        return jsonify({
            "type": "FeatureCollection",
            "features": results
        })

    except Exception as e:
        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "warning": str(e)
        })


# -------------------------
# PARKING
# -------------------------
@app.route("/api/nearby_parking")
def nearby_parking():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))
        radius = float(request.args.get("radius", 200))

        results = []

        for p in PARKING:
            try:
                plat = float(p.get("lat"))
                plon = float(p.get("lon"))

                d = distance_m(lat, lon, plat, plon)
                if d <= radius:
                    results.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [plon, plat]
                        },
                        "properties": {
                            "id": p.get("id"),
                            "name": p.get("name") or f"Parking {p.get('id')}",
                            "type": "parking",
                            "capacity": p.get("capacity"),
                            "fee": p.get("fee"),
                            "parking_type": p.get("parking_type"),
                            "surface": p.get("surface"),
                            "distance": round(d)
                        }
                    })
            except Exception:
                continue

        return jsonify({
            "type": "FeatureCollection",
            "features": results
        })

    except Exception as e:
        return jsonify({
            "type": "FeatureCollection",
            "features": [],
            "warning": str(e)
        })


# -------------------------
# MAP VIEW
# -------------------------
@app.route("/map")
def map_view():
    return render_template("map.html", mapbox_token=os.getenv("MAPBOX_TOKEN", ""))


# -------------------------
# HEALTH
# -------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)