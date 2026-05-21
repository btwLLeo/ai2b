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

import json

def carica_eventi_reali(file_json="eventi.json"):

    print("Inizio caricamento degli eventi reali da JSON...")
    """
    Legge il JSON reale degli eventi, calcola gli embedding e li carica su Qdrant.
    """
    print(f"Lettura del file eventi ({file_json}) in corso...")
    with open(file_json, "r", encoding="utf-8") as f:
        dati_eventi = json.load(f)

    points = []
    
    for evento in dati_eventi:
        # 1. Estraiamo il testo da vettorizzare (contiene già titolo, descr, ecc.)
        testo_da_vettorizzare = evento["text_to_embed"]
        
        # 2. Calcoliamo l'embedding
        vettore = get_real_embedding(testo_da_vettorizzare)
        
        # 3. Estraiamo le coordinate dal formato del tuo JSON
        lat = evento["metadata"]["location"]["latitude"]
        lon = evento["metadata"]["location"]["longitude"]
        
        # 4. Prepariamo il payload (salviamo anche altri dati utili per l'LLM)
        payload = {
            "title": evento["title"],
            "text_to_embed": testo_da_vettorizzare,
            "location": {"lat": lat, "lon": lon}, # Formato richiesto dall'indice geo di Qdrant
            "location_name": evento["metadata"]["location"]["name"],
            "url": evento["metadata"].get("url", ""),
            "schedule": evento["metadata"]["schedule"]["text_summary"]
        }
        
        # 5. Creiamo il punto Qdrant
        points.append(
            PointStruct(
                id=evento["id"],
                vector=vettore,
                payload=payload
            )
        )

    # 6. Caricamento a blocchi (batch processing)
    batch_size = 50
    print(f"Inizio caricamento di {len(points)} eventi su Qdrant...")
    
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(
            collection_name="events_collection",
            points=batch
        )
        print(f" -> Caricati {i + len(batch)} / {len(points)} eventi")
        
    print("✅ Tutti gli eventi reali caricati con successo!\n")

# Chiamata alla funzione (assicurati che il percorso del file sia corretto)
carica_eventi_reali("eventi_trento_puliti.json")

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

def get_logistics_context(event_id, radius_meters=500):
    """
    Recupera l'evento e restituisce una stringa formattata con i servizi vicini
    da passare all'LLM.
    """
    # 1. Recupero Evento
    event_record = client.retrieve(
        collection_name="events_collection", ids=[event_id]
    )[0]
    coords = event_record.payload["location"]
    
    # 2. Ricerca Parcheggi (limitiamo a 3 per non confondere l'LLM)
    nearby_parking = client.scroll(
        collection_name="parking_collection",
        scroll_filter=Filter(must=[
            FieldCondition(key="location", geo_radius=GeoRadius(center=coords, radius=radius_meters))
        ]),
        limit=3,
        with_payload=True,
    )[0]

    # 3. Ricerca Bus (limitiamo a 3)
    nearby_transit = client.scroll(
        collection_name="transit_collection",
        scroll_filter=Filter(must=[
            FieldCondition(key="location", geo_radius=GeoRadius(center=coords, radius=radius_meters))
        ]),
        limit=3,
        with_payload=True,
    )[0]

    # 4. Formattazione del Contesto Testuale per l'LLM
    context_str = f"EVENTO TROVATO:\n- Titolo: {event_record.payload['title']}\n- Dettagli: {event_record.payload['text_to_embed']}\n\n"
    
    context_str += "PARCHEGGI NELLE VICINANZE (Max 500m):\n"
    if nearby_parking:
        for p in nearby_parking:
            context_str += f"- {p.payload['raw_text']}\n"
    else:
        context_str += "- Nessun parcheggio mappato nelle immediate vicinanze.\n"

    context_str += "\nFERMATE AUTOBUS NELLE VICINANZE (Max 500m):\n"
    if nearby_transit:
        for t in nearby_transit:
            context_str += f"- {t.payload['raw_text']}\n"
    else:
        context_str += "- Nessuna fermata mappata nelle immediate vicinanze.\n"

    return context_str

def gestisci_richiesta_utente(user_prompt: str):
    print(f"\n🗣️ Utente chiede: '{user_prompt}'")
    print("🔍 Sto cercando l'evento e la logistica...")

    # 1. Convertiamo la domanda in Vettore
    query_vector = get_real_embedding(user_prompt)

    # 2. Ricerca Semantica: Trova l'evento più pertinente (Nuova API)
    risposta_qdrant = client.query_points(
        collection_name="events_collection",
        query=query_vector,
        limit=1
    )
    
    search_results = risposta_qdrant.points

    if not search_results:
        return "Non ho trovato eventi pertinenti a questa richiesta."

    top_event = search_results[0]
    event_id = top_event.id
    
    # top_event.score contiene la % di similitudine (da 0 a 1)
    if top_event.score < 0.2:
        return "Mi spiace, non ci sono eventi a Trento che corrispondono esattamente alla tua richiesta in questo momento."

    # 3. Estraiamo il contesto logistico (GeoRadius Search)
    context_testuale = get_logistics_context(event_id=event_id, radius_meters=500)

    # 4. INGEGNERIA DEL PROMPT: Costruiamo il messaggio per l'LLM
    system_prompt = f"""Sei un assistente turistico e logistico virtuale per la città di Trento.
Il tuo compito è rispondere alla domanda dell'utente in modo colloquiale, gentile e molto pratico.

REGOLA 1: Usa SOLO le informazioni fornite nel CONTESTO qui sotto. Non inventare eventi o parcheggi che non esistono.
REGOLA 2: Rispondi prima alla richiesta sull'evento, poi aggiungi autonomamente le informazioni utili su parcheggi e mezzi pubblici per raggiungerlo.

--- INIZIO CONTESTO RECUPERATO DAL DATABASE ---
{context_testuale}
--- FINE CONTESTO ---

Domanda dell'utente: {user_prompt}
Risposta:"""

    return system_prompt

# --- TESTIAMO IL SISTEMA ---
domanda = "Posso morire?"
prompt_finale = gestisci_richiesta_utente(domanda)

print("\n================== PROMPT PER LLM ==================")
print(prompt_finale)
print("====================================================")