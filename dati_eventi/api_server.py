from flask import Flask, request, jsonify
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    GeoRadius,
    PointStruct,
    VectorParams,
)

app = Flask(__name__)

# Initialize Qdrant client in-memory
client = QdrantClient(":memory:")
VECTOR_DIM = 4

def get_mock_embedding():
    """Simulates vector embedding generation."""
    return np.random.rand(VECTOR_DIM).tolist()

# Create collections
collections = ["events_collection", "parking_collection", "transit_collection"]

for col in collections:
    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

# Create geospatial indexes
for col in collections:
    client.create_payload_index(
        collection_name=col,
        field_name="location",
        field_schema="geo",
    )

# Populate sample data (Trento)
museo_lat, museo_lon = 46.020998, 11.126958
client.upsert(
    collection_name="events_collection",
    points=[
        PointStruct(
            id=3651,
            vector=get_mock_embedding(),
            payload={
                "title": "Attività al Museo dell'aeronautica Gianni Caproni",
                "text_to_embed": "Utilizzo dei simulatori di volo e visita guidata...",
                "location": {"lat": museo_lat, "lon": museo_lon},
            },
        )
    ],
)

client.upsert(
    collection_name="parking_collection",
    points=[
        PointStruct(
            id=1,
            vector=get_mock_embedding(),
            payload={
                "name": "Parcheggio Museo Caproni (Vicinissimo)",
                "stalli": 50,
                "location": {"lat": 46.0215, "lon": 11.1272},
            },
        ),
        PointStruct(
            id=2,
            vector=get_mock_embedding(),
            payload={
                "name": "Parcheggio Duomo Trento (Fuori Raggio)",
                "stalli": 120,
                "location": {"lat": 46.0666, "lon": 11.1214},
            },
        ),
    ],
)

client.upsert(
    collection_name="transit_collection",
    points=[
        PointStruct(
            id=101,
            vector=get_mock_embedding(),
            payload={
                "stop_name": "Fermata Mattarello / Museo Caproni",
                "lines": ["7", "A"],
                "location": {"lat": 46.0220, "lon": 11.1260},
            },
        )
    ],
)

def hybrid_geospatial_retrieval(event_id, radius_meters=500):
    """Finds an event and searches for parking and transit within its radius."""
    
    # 1. Retrieve event coordinates
    event_record = client.retrieve(
        collection_name="events_collection", ids=[event_id]
    )[0]
    coords = event_record.payload["location"]
    title = event_record.payload["title"]

    # 2. Search for nearby parking
    nearby_parking = client.scroll(
        collection_name="parking_collection",
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="location",
                    geo_radius=GeoRadius(
                        center={"lat": coords["lat"], "lon": coords["lon"]},
                        radius=radius_meters,
                    )
                )
            ]
        ),
        with_payload=True,
        with_vectors=False,
    )[0]

    # 3. Search for nearby transit
    nearby_transit = client.scroll(
        collection_name="transit_collection",
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="location",
                    geo_radius=GeoRadius(
                        center={"lat": coords["lat"], "lon": coords["lon"]},
                        radius=radius_meters,
                    )
                )
            ]
        ),
        with_payload=True,
        with_vectors=False,
    )[0]

    return {
        "event": {
            "id": event_id,
            "title": title,
            "location": coords
        },
        "radius_meters": radius_meters,
        "parking": [
            {
                "name": p.payload["name"],
                "stalli": p.payload.get("stalli", 0),
                "location": p.payload["location"]
            }
            for p in nearby_parking
        ],
        "transit": [
            {
                "stop_name": t.payload["stop_name"],
                "lines": t.payload["lines"],
                "location": t.payload["location"]
            }
            for t in nearby_transit
        ]
    }

@app.route('/api/hybrid_geospatial_retrieval', methods=['GET'])
def api_hybrid_geospatial_retrieval():
    """API endpoint for hybrid geospatial retrieval."""
    try:
        event_id = request.args.get('event_id', type=int, default=3651)
        radius_meters = request.args.get('radius_meters', type=int, default=500)
        
        result = hybrid_geospatial_retrieval(event_id, radius_meters)
        return jsonify(result), 200
    except IndexError:
        return jsonify({"error": f"Event with ID {event_id} not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "message": "API is running"}), 200

if __name__ == '__main__':
    print("Starting Hybrid Geospatial Retrieval API Server...")
    print("Available endpoints:")
    print("  GET /api/health")
    print("  GET /api/hybrid_geospatial_retrieval?event_id=3651&radius_meters=500")
    app.run(debug=True, host='127.0.0.1', port=5000)
