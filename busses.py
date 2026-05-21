"""
osm_buses.py
Fetch bus stops and bus lines for a given city using the Overpass API.
"""

from __future__ import annotations

import json
import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {
    "User-Agent": "osm-buses.py/1.0 (personal script)",
    "Accept": "application/json",
}


def _escape_ql_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _run_query(query: str) -> list[dict]:
    """Send an Overpass QL query and return the elements list."""
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=90,
    )

    if not response.ok:
        raise RuntimeError(
            f"Overpass HTTP {response.status_code}: {response.text[:500]}"
        )

    data = response.json()
    return data.get("elements", [])


def get_bus_stops(city: str) -> list[dict]:
    """
    Fetch all bus stops in a city.

    Returns a list of dicts with keys:
        id, lat, lon, name, ref
    """
    city_q = _escape_ql_string(city)

    query = f"""
[out:json][timeout:60];
rel["boundary"="administrative"]["name"="{city_q}"]["admin_level"="8"];
map_to_area -> .searchArea;
(
  node["highway"="bus_stop"](area.searchArea);
  node["public_transport"="platform"](area.searchArea);
);
out body;
"""

    elements = _run_query(query)

    stops = []
    for el in elements:
        tags = el.get("tags", {})
        stops.append({
            "id": el.get("id"),
            "lat": el.get("lat"),
            "lon": el.get("lon"),
            "name": tags.get("name", ""),
            "ref": tags.get("ref", ""),
        })
    return stops


def get_bus_lines(city: str) -> list[dict]:
    """
    Fetch all bus route relations in a city.

    Returns a list of dicts with keys:
        id, name, ref, operator, from, to, colour
    """
    city_q = _escape_ql_string(city)

    query = f"""
[out:json][timeout:60];
rel["boundary"="administrative"]["name"="{city_q}"]["admin_level"="8"];
map_to_area -> .searchArea;
relation["type"="route"]["route"="bus"](area.searchArea);
out tags;
"""

    elements = _run_query(query)

    lines = []
    for el in elements:
        tags = el.get("tags", {})
        lines.append({
            "id": el.get("id"),
            "name": tags.get("name", ""),
            "ref": tags.get("ref", ""),
            "operator": tags.get("operator", ""),
            "from": tags.get("from", ""),
            "to": tags.get("to", ""),
            "colour": tags.get("colour", ""),
        })
    return lines


if __name__ == "__main__":
    city = input("Enter city name: ").strip()
    if not city:
        raise SystemExit("City name cannot be empty.")

    print(f"\nFetching bus stops in {city!r}...")
    stops = get_bus_stops(city)
    print(f"Found {len(stops)} bus stops.")
    print(json.dumps(stops[:5], indent=2), "..." if len(stops) > 5 else "")

    print(f"\nFetching bus lines in {city!r}...")
    lines = get_bus_lines(city)
    print(f"Found {len(lines)} bus lines.")
    print(json.dumps(lines[:5], indent=2), "..." if len(lines) > 5 else "")