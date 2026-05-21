"""
osm_parking.py
Fetch parking spaces and parking lots for a given city using the Overpass API.
"""

from __future__ import annotations

import json
from typing import Any

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {
    "User-Agent": "osm-parking.py/1.0 (personal script)",
    "Accept": "application/json",
}


def _split_tags(value: str) -> set[str]:
    value = value.lower().strip()
    for sep in [",", "|", "/", ";"]:
        value = value.replace(sep, " ")
    return {part for part in value.split() if part}


def _is_restricted_private(tags: dict[str, Any]) -> bool:
    fields = [
        tags.get("access", ""),
        tags.get("access:conditional", ""),
        tags.get("parking:condition:access", ""),
    ]

    tokens: set[str] = set()
    for field in fields:
        tokens |= _split_tags(field)

    return bool(tokens & {"private", "customers", "customer", "consumers"})

def _escape_ql_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _run_query(query: str) -> list[dict[str, Any]]:
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=90,
    )
    response.raise_for_status()
    return response.json().get("elements", [])


def get_parking(city: str) -> list[dict[str, Any]]:
    """
    Fetch all parking amenities (nodes, ways, and relations) in a city.

    Returns a list of dicts with keys:
        id, type, lat, lon,
        name, access, capacity,
        fee, parking_type, surface
    """
    city_q = _escape_ql_string(city)

    query = f"""
[out:json][timeout:90];
rel["boundary"="administrative"]["name"="{city_q}"]["admin_level"="8"];
map_to_area -> .searchArea;
(
  node["amenity"="parking"](area.searchArea);
  way["amenity"="parking"](area.searchArea);
  relation["amenity"="parking"](area.searchArea);
);
out center tags;
"""

    elements = _run_query(query)

    parking_list: list[dict[str, Any]] = []
    for el in elements:
        tags = el.get("tags", {})

        # Ways expose computed centers
        center = el.get("center", {})

        lat = el.get("lat")
        if lat is None:
            lat = center.get("lat")

        lon = el.get("lon")
        if lon is None:
            lon = center.get("lon")

        name = tags.get("name", "")
        access = tags.get("access", "").lower()

        #        name = tags.get("name", "")

        # Ignore truck parking / heavy vehicle rest areas
        if (
            "mezzi pesanti" in name.lower()
            or "truck" in name.lower()
            or tags.get("hgv", "").lower() == "yes"
            or tags.get("parking", "").lower() == "truck"
        ):
            continue

        # Drop private / customer-only parking even if the value is mixed
        fee = tags.get("fee", "").lower()

        # Remove restricted parking ONLY if it is not paid public parking
        #
        # Many public garages are tagged as:
        #   access=customers
        #   fee=yes
        #
        # and should still be included.
        if _is_restricted_private(tags) and fee not in {"yes", "paid"}:
            continue

        access = tags.get("access", "").lower()

        if access in {"yes", "public", ""}:
            normalized_access = "public"
        else:
            normalized_access = access

        parking_list.append({
            "id": el.get("id"),
            "type": el.get("type"),
            "lat": lat,
            "lon": lon,
            "name": name,
            "access": normalized_access,
            "capacity": tags.get("capacity", ""),
            "fee": tags.get("fee", ""),
            "parking_type": tags.get("parking", ""),
            "surface": tags.get("surface", ""),
        })

    return parking_list


if __name__ == "__main__":
    city = input("Enter city name: ").strip()
    if not city:
        raise SystemExit("City name cannot be empty.")

    print(f"\nFetching parking in {city!r}...")
    parking = get_parking(city)
    filename = f"{city.lower().replace(' ', '_')}_parking.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(parking, f, indent=2, ensure_ascii=False)

    print(f"Saved parking data to '{filename}'")
    print(f"Found {len(parking)} parking locations.")
    print(json.dumps(parking, indent=2))