from bs4 import BeautifulSoup

def clean_html(html_text):
    if not html_text:
        return ""
    # Rimuove i tag HTML e pulisce gli spazi bianchi
    soup = BeautifulSoup(html_text, "html.parser")
    return " ".join(soup.get_text().split())

def process_trento_event(raw_event):
    content_data = raw_event.get("content", {})
    ita_data = content_data.get("data", {}).get("ita-IT", {})
    extradata = content_data.get("extradata", {}).get("ita-IT", {})
    
    # 1. Estrazione e pulizia del testo per l'embedding
    title = ita_data.get("event_title", raw_event.get("title", ""))
    abstract = clean_html(ita_data.get("event_abstract", ""))
    description = clean_html(ita_data.get("description", ""))
    
    typologies = ", ".join(ita_data.get("has_public_event_typology", []))
    target = ita_data.get("about_target_audience", "")
    cost_info = clean_html(ita_data.get("cost_notes", ""))
    is_free = "Gratuito" if ita_data.get("is_accessible_for_free") == 1 else "A pagamento"
    
    # Costruiamo un unico saggio testuale denso di informazioni utili
    text_pieces = [
        f"Titolo: {title}.",
        f"Categorie: {typologies}." if typologies else "",
        f"Destinatari: {target}." if target else "",
        f"Descrizione: {abstract} {description}".strip(),
        f"Informazioni costi: {is_free}. {cost_info}" if cost_info else f"Costi: {is_free}."
    ]
    text_to_embed = " ".join([p for p in text_pieces if p])
    
    # 2. Estrazione Geografica
    geo_list = extradata.get("geo", [])
    lat, lon = None, None
    if geo_list:
        lat = float(geo_list[0].get("latitude"))
        lon = float(geo_list[0].get("longitude"))
        
    # 3. Estrazione Luogo
    location_name = ""
    places = ita_data.get("takes_place_in", [])
    if places:
        location_name = places[0].get("name", {}).get("ita-IT", "")

    # 4. Ricostruzione URL originale (usando l'alias nel JSON)
    url_alias = extradata.get("urlAlias", "")
    full_url = f"https://eventi.comune.trento.it{url_alias}" if url_alias else ""

    # 5. Formattazione finale
    cleaned_record = {
        "id": raw_event.get("id"),
        "title": title,
        "text_to_embed": text_to_embed,
        "metadata": {
            "source": "comune_trento_events",
            "url": full_url,
            "location": {
                "name": location_name,
                "latitude": lat,
                "longitude": lon
            },
            "schedule": {
                "text_summary": ita_data.get("time_interval", {}).get("text", ""),
                "next_upcoming_start": raw_event.get("start"),
                "next_upcoming_end": raw_event.get("end")
            }
        }
    }
    return cleaned_record

# Esempio di utilizzo con il tuo record (assumendo sia salvato nella variabile 'evento_grezzo')
# record_pulito = process_trento_event(evento_grezzo)

from datetime import datetime, timedelta
import requests


def fetch_trento_events():
    """Effettua la richiesta all'API OpenData del Comune di Trento

    per ottenere gli eventi della settimana corrente.
    """
    api_url = "https://eventi.comune.trento.it/opendata/api/calendar/search/"

    # Calcoliamo le date dinamicamente basandoci su oggi (Maggio 2026)
    # L'API si aspetta filtri temporali per mostrare solo gli eventi rilevanti
    oggi = datetime.now()
    inizio_settimana = oggi.strftime("%Y-%m-%dT00:00:00+02:00")
    # Es. prendiamo i prossimi 7 giorni di eventi
    fine_settimana = (oggi + timedelta(days=7)).strftime(
        "%Y-%m-%dT00:00:00+02:00"
    )
    data_filtro_raw = oggi.strftime("%Y-%m-%d 00:00")

    # Stringa di query (q) per l'endpoint di Trento
    # Filtra per la classe 'event', esclude le raccolte e imposta il range temporale
    query_string = (
        f"classes [event] and subtree [65] and state in [moderation.skipped,moderation.accepted] "
        f"sort [time_interval=>asc] and raw[extra_event_collection_i] = 0 "
        f"and calendar[time_interval] = [{data_filtro_raw},*]"
    )

    # Parametri della richiesta HTTP
    params = {
        "q": query_string,
        "start": inizio_settimana,
        "end": fine_settimana,
        "limit": 50,  # Quanti eventi scaricare per pagina (l'API di solito supporta la paginazione)
        "offset": 0,
    }

    headers = {
        "User-Agent": "GeospatialRAGBot/1.0 (Python requests)",
        "Accept": "application/json",
    }

    all_events = []

    print(f"Avvio il download degli eventi a partire da: {oggi.strftime('%d-%m-%Y')}...")

    while True:
        try:
            response = requests.get(
                api_url, params=params, headers=headers, timeout=15
            )

            # Se l'API restituisce un errore (es. 404, 500), lancia un'eccezione
            response.raise_for_status()

            data = response.json()

            # L'API restituisce una lista di eventi direttamente o dentro una chiave (es. 'nodes' o 'results')
            # In base alla struttura standard del portale della città, di solito restituisce una lista di oggetti JSON
            events_page = data if isinstance(data, list) else data.get("nodes", data.get("results", []))

            if not events_page:
                break

            all_events.extend(events_page)
            print(
                f"Scaricati {len(events_page)} eventi (Totale parziale: {len(all_events)})"
            )

            # Se la pagina è parziale o abbiamo scaricato meno del limite, abbiamo finito
            if len(events_page) < params["limit"] or isinstance(data, list):
                break

            # Altrimenti avanziamo alla pagina successiva
            params["offset"] += params["limit"]

        except requests.exceptions.HTTPError as http_err:
            print(f"Errore HTTP: {http_err}")
            break
        except Exception as err:
            print(f"Si è verificato un errore: {err}")
            break

    print(f"Download completato. Ricevuti {len(all_events)} eventi grezzi.")
    return all_events


import json
from datetime import datetime, timedelta


# ... (tieni pure intatte le tue funzioni clean_html, process_trento_event e fetch_trento_events)

if __name__ == "__main__":
    # 1. Scarica i dati grezzi
    eventi_grezzi = fetch_trento_events()

    # 2. Cicla e pulisci ogni evento
    eventi_puliti = []
    for ev in eventi_grezzi:
        try:
            record_pulito = process_trento_event(ev)
            eventi_puliti.append(record_pulito)
        except Exception as e:
            print(
                f"Impossibile elaborare l'evento ID {ev.get('id', 'Sconosciuto')}: {e}"
            )

    print(f"Pronti {len(eventi_puliti)} record puliti per il database RAG!")

    # 3. Salva la lista in un file JSON
    nome_file = "eventi_trento_puliti.json"

    try:
        with open(nome_file, "w", encoding="utf-8") as f:
            # indent=4 rende il file JSON leggibile e formattato bene per gli umani
            # ensure_ascii=False mantiene intatte le lettere accentate italiane
            json.dump(eventi_puliti, f, indent=4, ensure_ascii=False)

        print(f"🎉 Successo! I dati sono stati salvati in '{nome_file}'")

    except IOError as e:
        print(f"Errore durante il salvataggio del file: {e}")