import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    CollectionDescription,
    Distance,
    Filter,
    FieldCondition,  # <-- Aggiungi questo
    GeoRadius,
    PointStruct,
    VectorParams,
)

# 1. Inizializziamo il client di Qdrant in memoria
client = QdrantClient(":memory:")
VECTOR_DIM = 4  # Usiamo 4 dimensioni per semplicità (es. OpenAI ne usa 1536)


def get_mock_embedding():
    """Simula la generazione di un embedding vettoriale."""
    return np.random.rand(VECTOR_DIM).tolist()


# 2. Creiamo le tre collection nel database vettoriale
collections = ["events_collection", "parking_collection", "transit_collection"]

for col in collections:
    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

# 3. CONFIGURAZIONE CHIAVE: Creiamo l'indice Geospaziale sui payload
# Questo dice a Qdrant che il campo "location" contiene coordinate [lat, lon] su cui fare calcoli geografici
for col in collections:
    client.create_payload_index(
        collection_name=col,
        field_name="location",
        field_schema="geo",  # Definisce il tipo di indice come geografico
    )

print("✅ Database e indici geografici inizializzati con successo.\n")

# --- POPOLAMENTO DATI DI ESEMPIO (TRENTO) ---

# Inseriamo l'evento del Museo Caproni (dal tuo dataset)
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

# Inseriamo due parcheggi simulati: uno vicino (100m) e uno fuori raggio (2km, a Trento Centro)
client.upsert(
    collection_name="parking_collection",
    points=[
        PointStruct(
            id=1,
            vector=get_mock_embedding(),
            payload={
                "name": "Parcheggio Museo Caproni (Vicinissimo)",
                "stalli": 50,
                "location": {
                    "lat": 46.0215,
                    "lon": 11.1272,
                },  # Circa 70 metri a Nord-Est
            },
        ),
        PointStruct(
            id=2,
            vector=get_mock_embedding(),
            payload={
                "name": "Parcheggio Duomo Trento (Fuori Raggio)",
                "stalli": 120,
                "location": {
                    "lat": 46.0666,
                    "lon": 11.1214,
                },  # Circa 5 km a Nord
            },
        ),
    ],
)

# Inseriamo una fermata del bus vicina
client.upsert(
    collection_name="transit_collection",
    points=[
        PointStruct(
            id=101,
            vector=get_mock_embedding(),
            payload={
                "stop_name": "Fermata Mattarello / Museo Caproni",
                "lines": ["7", "A"],
                "location": {"lat": 46.0220, "lon": 11.1260},  # Circa 130 metri
            },
        )
    ],
)

print("✅ Dati inseriti nelle rispettive collection.\n")

# --- PIPELINE DI RETRIEVAL (RICERCA A RAGGIO) ---


def hybrid_geospatial_retrieval(event_id, radius_meters=500):
    """Trova un evento specifico e cerca parcheggi e bus nel suo raggio d'azione."""
    print(f"--- Esecuzione Retrieval per Evento ID {event_id} ---")

    # 1. Recuperiamo le coordinate dell'evento cercato
    event_record = client.retrieve(
        collection_name="events_collection", ids=[event_id]
    )[0]
    coords = event_record.payload["location"]
    title = event_record.payload["title"]

    print(
        f"Evento: '{title}' trovato alle coordinate: Lat {coords['lat']}, Lon {coords['lon']}"
    )
    print(f"Cerco servizi utili nel raggio di {radius_meters} metri...\n")

    # 2. Eseguiamo la GEO RADIUS SEARCH sulla collection Parcheggi
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

    # 3. Eseguiamo la stessa ricerca geografica sulle Fermate dei Bus
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

    # --- Stampa dei risultati che andranno a comporre il contesto della RAG ---
    print(f"🅿️ PARCHEGGI TROVATI ENTRO {radius_meters}m:")
    for p in nearby_parking:
        print(
            f" - {p.payload['name']} (Coordinate: {p.payload['location']['lat']}, {p.payload['location']['lon']})"
        )

    print(f"\n🚌 TRASPORTO PUBBLICO TROVATO ENTRO {radius_meters}m:")
    for t in nearby_transit:
        print(
            f" - {t.payload['stop_name']} [Linee: {', '.join(t.payload['lines'])}]"
        )


# Eseguiamo la funzione di test cercando l'evento del museo Caproni
hybrid_geospatial_retrieval(event_id=3651, radius_meters=500)