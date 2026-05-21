from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    GeoRadius,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer # <-- 1. Importiamo il modello

# 2. Inizializziamo il modello di embedding (scaricherà i pesi la prima volta che lo avvii)
print("Caricamento del modello di embedding in corso...")
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# Il modello MiniLM genera vettori a 384 dimensioni (non più 4)
VECTOR_DIM = 384 

# Funzione per calcolare il vero embedding da un testo
def get_real_embedding(text: str):
    """Trasforma una stringa di testo in un vettore numerico reale."""
    # encode() calcola il vettore, tolist() lo converte in un formato compatibile con Qdrant
    return embedder.encode(text).tolist()


# 3. Inizializziamo il client di Qdrant
client = QdrantClient(":memory:")
collections = ["events_collection", "parking_collection", "transit_collection"]

for col in collections:
    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

for col in collections:
    client.create_payload_index(
        collection_name=col,
        field_name="location",
        field_schema="geo",
    )

print("✅ Database e indici geografici inizializzati con successo.\n")

# --- POPOLAMENTO DATI DI ESEMPIO CON VERI EMBEDDING ---

museo_lat, museo_lon = 46.020998, 11.126958

# Testo che vogliamo che l'LLM "capisca" quando l'utente fa una ricerca
testo_evento = "Attività al Museo dell'aeronautica Gianni Caproni. Utilizzo dei simulatori di volo e visita guidata."

client.upsert(
    collection_name="events_collection",
    points=[
        PointStruct(
            id=3651,
            # 4. Calcoliamo l'embedding passando il testo alla nostra funzione
            vector=get_real_embedding(testo_evento),
            payload={
                "title": "Attività al Museo dell'aeronautica Gianni Caproni",
                "text_to_embed": testo_evento,
                "location": {"lat": museo_lat, "lon": museo_lon},
            },
        )
    ],
)

# Anche per i parcheggi usiamo una descrizione testuale per generare l'embedding
client.upsert(
    collection_name="parking_collection",
    points=[
        PointStruct(
            id=1,
            vector=get_real_embedding("Parcheggio pubblico coperto vicino al Museo Caproni con 50 stalli"),
            payload={
                "name": "Parcheggio Museo Caproni (Vicinissimo)",
                "stalli": 50,
                "location": {"lat": 46.0215, "lon": 11.1272},
            },
        ),
        PointStruct(
            id=2,
            vector=get_real_embedding("Parcheggio grande Duomo Trento centro città"),
            payload={
                "name": "Parcheggio Duomo Trento (Fuori Raggio)",
                "stalli": 120,
                "location": {"lat": 46.0666, "lon": 11.1214},
            },
        ),
    ],
)

# E per i bus
client.upsert(
    collection_name="transit_collection",
    points=[
        PointStruct(
            id=101,
            vector=get_real_embedding("Fermata dell'autobus Mattarello Museo Caproni linee 7 e A"),
            payload={
                "stop_name": "Fermata Mattarello / Museo Caproni",
                "lines": ["7", "A"],
                "location": {"lat": 46.0220, "lon": 11.1260},
            },
        )
    ],
)

print("✅ Dati caricati e vettorizzati semanticamente!\n")

# --- PIPELINE DI RETRIEVAL ---
# (La funzione rimane identica a prima, ma ora i dati nel DB sono reali)
def hybrid_geospatial_retrieval(event_id, radius_meters=500):
    print(f"--- Esecuzione Retrieval per Evento ID {event_id} ---")

    event_record = client.retrieve(
        collection_name="events_collection", ids=[event_id]
    )[0]
    coords = event_record.payload["location"]
    title = event_record.payload["title"]

    print(f"Evento: '{title}' trovato alle coordinate: Lat {coords['lat']}, Lon {coords['lon']}")
    print(f"Cerco servizi utili nel raggio di {radius_meters} metri...\n")

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

    print(f"🅿️ PARCHEGGI TROVATI ENTRO {radius_meters}m:")
    for p in nearby_parking:
        print(f" - {p.payload['name']}")

    print(f"\n🚌 TRASPORTO PUBBLICO TROVATO ENTRO {radius_meters}m:")
    for t in nearby_transit:
        print(f" - {t.payload['stop_name']} [Linee: {', '.join(t.payload['lines'])}]")

hybrid_geospatial_retrieval(event_id=3651, radius_meters=500)