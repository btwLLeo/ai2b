from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    GeoPoint,
    GeoRadius,
    PointStruct,
    VectorParams,
)
from sentence_transformers import SentenceTransformer


EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIM = 384


@dataclass
class DataPaths:
    events_json: Path
    parking_json: Path
    stops_json: Path


class TrentoLogisticsAssistant:
    """Pipeline riusabile: inizializza una sola volta e poi risponde alle domande."""

    def __init__(
        self,
        qdrant_path: str = "./qdrant_data",
        embed_model_name: str = EMBED_MODEL_NAME,
        llm_fn: Optional[Callable[[str], str]] = None,
    ) -> None:
        # Persistenza locale: non usare ":memory:" se vuoi tenere i dati tra un avvio e l'altro.
        self.client = QdrantClient(path=qdrant_path)
        self.embedder = SentenceTransformer(embed_model_name)
        self.llm_fn = llm_fn

        self.collections = {
            "events": "events_collection",
            "parking": "parking_collection",
            "transit": "transit_collection",
        }

    # -----------------------------
    # Utils embedding e testo
    # -----------------------------
    def get_embedding(self, text: str) -> list[float]:
        return self.embedder.encode(text, normalize_embeddings=True).tolist()

    @staticmethod
    def genera_descrizione_parcheggio(p: dict) -> str:
        nome = p.get("name") or "Parcheggio"
        dettagli = [nome]

        if p.get("parking_type"):
            dettagli.append(f"Tipo: {p['parking_type'].replace('_', ' ')}")
        if p.get("capacity"):
            dettagli.append(f"Capacità: {p['capacity']} posti")
        if p.get("access"):
            dettagli.append(f"Accesso: {p['access']}")
        if p.get("fee"):
            costo = (
                "a pagamento"
                if p["fee"] == "yes"
                else "gratuito"
                if p["fee"] == "no"
                else p["fee"]
            )
            dettagli.append(f"Tariffa: {costo}")

        return " - ".join(dettagli)

    @staticmethod
    def genera_descrizione_fermata(stop: dict) -> str:
        nome = stop.get("name") or "Fermata Autobus"
        dettagli = [nome]
        if stop.get("ref"):
            dettagli.append(f"Rif/Linea: {stop['ref']}")
        return " - ".join(dettagli)

    # -----------------------------
    # Setup una tantum
    # -----------------------------
    def initialize_collections(self, recreate: bool = False) -> None:
        for col in self.collections.values():
            if recreate:
                self.client.recreate_collection(
                    collection_name=col,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                )
            else:
                exists = self.client.collection_exists(col)
                if not exists:
                    self.client.create_collection(
                        collection_name=col,
                        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                    )

            # Indice geo sul campo payload "location"
            # Se il payload index esiste già, Qdrant può segnalare errore a seconda della versione.
            # Per questo lo creiamo solo se la collezione è nuova o ricreata.
            if recreate or not self.client.collection_exists(col):
                self.client.create_payload_index(
                    collection_name=col,
                    field_name="location",
                    field_schema="geo",
                )

    def _upsert_in_batches(self, collection_name: str, points: list[PointStruct], batch_size: int = 100) -> None:
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=collection_name, points=batch)

    def load_events(self, file_json: str) -> None:
        with open(file_json, "r", encoding="utf-8") as f:
            dati_eventi = json.load(f)

        points: list[PointStruct] = []
        for evento in dati_eventi:
            testo = evento["text_to_embed"]
            vettore = self.get_embedding(testo)
            lat = evento["metadata"]["location"]["latitude"]
            lon = evento["metadata"]["location"]["longitude"]

            payload = {
                "title": evento.get("title", ""),
                "text_to_embed": testo,
                "location": {"lat": lat, "lon": lon},
                "location_name": evento["metadata"]["location"].get("name", ""),
                "url": evento["metadata"].get("url", ""),
                "schedule": evento["metadata"]["schedule"].get("text_summary", ""),
            }

            points.append(
                PointStruct(
                    id=evento["id"],
                    vector=vettore,
                    payload=payload,
                )
            )

        self._upsert_in_batches(self.collections["events"], points, batch_size=50)

    def load_parking(self, file_json: str) -> None:
        with open(file_json, "r", encoding="utf-8") as f:
            dati_parcheggi = json.load(f)

        points: list[PointStruct] = []
        for p in dati_parcheggi:
            testo = self.genera_descrizione_parcheggio(p)
            vettore = self.get_embedding(testo)

            payload = {
                "name": p.get("name") or "Parcheggio",
                "capacity": p.get("capacity") or "Non specificata",
                "fee": p.get("fee") or "Non specificata",
                "parking_type": p.get("parking_type") or "Non specificato",
                "location": {"lat": p["lat"], "lon": p["lon"]},
                "raw_text": testo,
            }

            points.append(
                PointStruct(
                    id=p["id"],
                    vector=vettore,
                    payload=payload,
                )
            )

        self._upsert_in_batches(self.collections["parking"], points, batch_size=100)

    def load_transit(self, file_json: str) -> None:
        with open(file_json, "r", encoding="utf-8") as f:
            dati_fermate = json.load(f)

        points: list[PointStruct] = []
        for stop in dati_fermate:
            testo = self.genera_descrizione_fermata(stop)
            vettore = self.get_embedding(testo)

            payload = {
                "name": stop.get("name") or "Fermata senza nome",
                "ref": stop.get("ref") or "Non specificato",
                "location": {"lat": stop["lat"], "lon": stop["lon"]},
                "raw_text": testo,
            }

            points.append(
                PointStruct(
                    id=stop["id"],
                    vector=vettore,
                    payload=payload,
                )
            )

        self._upsert_in_batches(self.collections["transit"], points, batch_size=100)

    def load_all_data(self, paths: DataPaths) -> None:
        self.initialize_collections(recreate=False)
        self.load_events(str(paths.events_json))
        self.load_parking(str(paths.parking_json))
        self.load_transit(str(paths.stops_json))

    # -----------------------------
    # Retrieval
    # -----------------------------
    def _get_event_by_id(self, event_id: int | str) -> dict:
        records = self.client.retrieve(
            collection_name=self.collections["events"],
            ids=[event_id],
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            raise ValueError(f"Evento non trovato: {event_id}")
        return records[0].payload

    def _geo_search(self, collection_name: str, coords: dict, radius_meters: int, limit: int = 3):
        return self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="location",
                        geo_radius=GeoRadius(
                            center=GeoPoint(lat=coords["lat"], lon=coords["lon"]),
                            radius=radius_meters,
                        ),
                    )
                ]
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )[0]

    def get_logistics_context(self, event_id: int | str, radius_meters: int = 500) -> str:
        event_payload = self._get_event_by_id(event_id)
        coords = event_payload["location"]

        nearby_parking = self._geo_search(
            self.collections["parking"], coords, radius_meters=radius_meters, limit=3
        )
        nearby_transit = self._geo_search(
            self.collections["transit"], coords, radius_meters=radius_meters, limit=3
        )

        context = (
            f"EVENTO TROVATO:\n"
            f"- Titolo: {event_payload.get('title', '')}\n"
            f"- Dettagli: {event_payload.get('text_to_embed', '')}\n\n"
        )

        context += "PARCHEGGI NELLE VICINANZE (Max 500m):\n"
        if nearby_parking:
            for p in nearby_parking:
                context += f"- {p.payload.get('raw_text', '')}\n"
        else:
            context += "- Nessun parcheggio mappato nelle immediate vicinanze.\n"

        context += "\nFERMATE AUTOBUS NELLE VICINANZE (Max 500m):\n"
        if nearby_transit:
            for t in nearby_transit:
                context += f"- {t.payload.get('raw_text', '')}\n"
        else:
            context += "- Nessuna fermata mappata nelle immediate vicinanze.\n"

        return context

    def search_event(self, user_prompt: str, min_score: float = 0.2):
        query_vector = self.get_embedding(user_prompt)
        response = self.client.query_points(
            collection_name=self.collections["events"],
            query=query_vector,
            limit=1,
        )
        points = response.points
        if not points:
            return None
        top = points[0]
        if top.score is not None and top.score < min_score:
            return None
        return top

    def build_prompt(self, user_prompt: str, context_testuale: str) -> str:
        return f"""Sei un assistente turistico e logistico virtuale per la città di Trento.
Il tuo compito è rispondere alla domanda dell'utente in modo colloquiale, gentile e molto pratico.

REGOLA 1: Usa SOLO le informazioni fornite nel CONTESTO qui sotto. Non inventare eventi o parcheggi che non esistono.
REGOLA 2: Rispondi prima alla richiesta sull'evento, poi aggiungi autonomamente le informazioni utili su parcheggi e mezzi pubblici per raggiungerlo.

--- INIZIO CONTESTO RECUPERATO DAL DATABASE ---
{context_testuale}
--- FINE CONTESTO ---

Domanda dell'utente: {user_prompt}
Risposta:"""

    def ask(self, user_prompt: str, radius_meters: int = 500) -> str:
        """Funzione runtime: non legge file, non ricrea il DB, usa solo il DB già caricato."""
        top_event = self.search_event(user_prompt)
        if not top_event:
            return "Non ho trovato eventi pertinenti a questa richiesta."

        event_id = top_event.id
        context = self.get_logistics_context(event_id=event_id, radius_meters=radius_meters)
        prompt_obj = {
            "id": event_id,
            "context": context
        } # self.build_prompt(user_prompt, context)
        prompt = json.dumps(prompt_obj, ensure_ascii=False)

        # Se colleghi un LLM, qui ottieni la risposta finale.
        if self.llm_fn is not None:
            return self.llm_fn(prompt)

        # Fallback utile per debug se non hai ancora agganciato il modello.
        return prompt_obj


# -----------------------------
# ESEMPIO D'USO
# -----------------------------
if __name__ == "__main__":
    assistant = TrentoLogisticsAssistant(qdrant_path="./qdrant_data")

    """ Esegui una sola volta quando devi popolare il DB """
    """ assistant.load_all_data(
        DataPaths(
            events_json=Path("eventi_trento_puliti.json"),
            parking_json=Path("../trento_parking.json"),
            stops_json=Path("../trento_stops.json"),
        )
    ) """

    # Da qui in poi, in produzione, chiami solo:
    risposta = assistant.ask("cerco un museo da visitare questo weekend con parcheggio nelle vicinanze")
    print(risposta)
    
