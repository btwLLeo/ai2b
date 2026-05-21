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

import json

def genera_descrizione_parcheggio(p):
    """
    Crea una stringa descrittiva del parcheggio ignorando i campi vuoti.
    Questo testo verrà trasformato in vettore e letto dall'LLM.
    """
    # Se non c'è il nome, lo chiamiamo genericamente "Parcheggio"
    nome = p.get("name") if p.get("name") else "Parcheggio"
    
    dettagli = [nome]
    
    if p.get("parking_type"):
        # Sostituiamo i trattini bassi con spazi (es. street_side -> street side)
        tipo = p["parking_type"].replace("_", " ")
        dettagli.append(f"Tipo: {tipo}")
        
    if p.get("capacity"):
        dettagli.append(f"Capacità: {p['capacity']} posti")
        
    if p.get("access"):
        dettagli.append(f"Accesso: {p['access']}")
        
    if p.get("fee"):
        # In OSM, fee="yes" o "no"
        costo = "a pagamento" if p["fee"] == "yes" else "gratuito" if p["fee"] == "no" else p["fee"]
        dettagli.append(f"Tariffa: {costo}")

    # Uniamo i pezzi: "Parcheggio - Tipo: street side - Accesso: public"
    return " - ".join(dettagli)


def carica_parcheggi_reali(file_json="parcheggi.json"):
    print("Inizio caricamento dei parcheggi reali da JSON...")
    """
    Legge il JSON reale, calcola gli embedding e fa l'upsert a blocchi.
    """
    print("Lettura del file parcheggi reali in corso...")
    with open(file_json, "r", encoding="utf-8") as f:
        dati_parcheggi = json.load(f)

    points = []
    
    for p in dati_parcheggi:
        # 1. Generiamo il testo da vettorizzare
        testo_descrittivo = genera_descrizione_parcheggio(p)
        
        # 2. Calcoliamo il vettore reale (usando la funzione dello step precedente)
        vettore = get_real_embedding(testo_descrittivo)
        
        # 3. Costruiamo il payload pulito, salvando solo ciò che ci serve
        payload = {
            "name": p.get("name") or "Parcheggio",
            "capacity": p.get("capacity") or "Non specificata",
            "fee": p.get("fee") or "Non specificata",
            "parking_type": p.get("parking_type") or "Non specificato",
            # Il campo location è FONDAMENTALE per la ricerca a raggio
            "location": {"lat": p["lat"], "lon": p["lon"]},
            "raw_text": testo_descrittivo # Utile da passare all'LLM
        }
        
        # 4. Creiamo il punto per Qdrant (OSM usa ID numerici giganti, Qdrant li accetta tranquillamente)
        points.append(
            PointStruct(
                id=p["id"],
                vector=vettore,
                payload=payload
            )
        )

    # 5. Facciamo l'upsert a blocchi (batch) di 100 elementi alla volta
    # Questo previene crash se hai migliaia di parcheggi nel file
    batch_size = 100
    print(f"Inizio caricamento di {len(points)} parcheggi su Qdrant...")
    
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name="parking_collection",
            points=batch
        )
        print(f" -> Caricati {i + len(batch)} / {len(points)} parcheggi")
        
    print("✅ Tutti i parcheggi reali caricati con successo!\n")

carica_parcheggi_reali("../trento_parking.json")

def genera_descrizione_fermata(stop):
    """
    Crea una stringa descrittiva per la fermata del bus.
    """
    # Se il nome non c'è, usiamo una dicitura generica
    nome = stop.get("name") if stop.get("name") else "Fermata Autobus"
    
    dettagli = [nome]
    
    # In OSM, 'ref' a volte contiene il numero della linea o il codice della fermata
    if stop.get("ref"):
        dettagli.append(f"Rif/Linea: {stop['ref']}")
        
    # Uniamo i pezzi: es. 'Mesiano / "Facoltà Ingegneria" - Rif/Linea: 5'
    return " - ".join(dettagli)


def carica_fermate_reali(file_json="fermate.json"):
    """
    Legge il JSON reale delle fermate, calcola gli embedding e fa l'upsert a blocchi.
    """
    print("Lettura del file fermate (stops) in corso...")
    with open(file_json, "r", encoding="utf-8") as f:
        dati_fermate = json.load(f)

    points = []
    
    for stop in dati_fermate:
        # 1. Generiamo il testo da vettorizzare
        testo_descrittivo = genera_descrizione_fermata(stop)
        
        # 2. Calcoliamo il vettore reale
        vettore = get_real_embedding(testo_descrittivo)
        
        # 3. Costruiamo il payload per Qdrant
        payload = {
            "name": stop.get("name") or "Fermata senza nome",
            "ref": stop.get("ref") or "Non specificato",
            # Struttura essenziale per la ricerca GeoRadius
            "location": {"lat": stop["lat"], "lon": stop["lon"]},
            "raw_text": testo_descrittivo
        }
        
        # 4. Creiamo il punto Qdrant usando l'ID nativo di OSM
        points.append(
            PointStruct(
                id=stop["id"],
                vector=vettore,
                payload=payload
            )
        )

    # 5. Upsert a blocchi (batch processing) per non intasare la memoria
    batch_size = 100
    print(f"Inizio caricamento di {len(points)} fermate su Qdrant...")
    
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name="transit_collection",
            points=batch
        )
        print(f" -> Caricate {i + len(batch)} / {len(points)} fermate")
        
    print("✅ Tutte le fermate reali caricate con successo!\n")

# Chiamata della funzione
carica_fermate_reali("../trento_stops.json")

print("✅ Dati caricati e vettorizzati semanticamente!\n")

# --- PIPELINE DI RETRIEVAL ---
# (La funzione rimane identica a prima, ma ora i dati nel DB sono reali)
def hybrid_geospatial_retrieval(event_id, radius_meters=3000):
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
        print(f" - {t.payload['name']}")

hybrid_geospatial_retrieval(event_id=3651, radius_meters=3000)