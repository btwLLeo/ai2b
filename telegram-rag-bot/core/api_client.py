"""
core/api_client.py — Client for dati_eventi hybrid geospatial retrieval API.

Provides methods to query events, parking, and transit information.
"""
import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class APIClient:
    """Client for the hybrid geospatial retrieval API."""

    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the API server (default: localhost:5000)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = 10

    def health_check(self) -> bool:
        """
        Check if the API server is running.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/health",
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def get_event_info(
        self,
        event_id: int = 3651,
        radius_meters: int = 500
    ) -> Optional[Dict[str, Any]]:
        """
        Get event info with nearby parking and transit stops.

        Args:
            event_id: Event ID to retrieve (default: 3651)
            radius_meters: Search radius in meters (default: 500)

        Returns:
            Dict with event, parking, and transit data, or None on error
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/hybrid_geospatial_retrieval",
                params={
                    "event_id": event_id,
                    "radius_meters": radius_meters
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Event {event_id} not found")
                return None
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Could not connect to API at {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None

    def format_event_response(self, data: Dict[str, Any]) -> str:
        """
        Format API response into a readable message.

        Args:
            data: Response dict from get_event_info()

        Returns:
            Formatted string for Telegram
        """
        if not data:
            return "No information available."

        event = data.get("event", {})
        parking = data.get("parking", [])
        transit = data.get("transit", [])

        lines = []

        # Event section
        lines.append(f"📍 *Event: {event.get('title', 'Unknown')}*")
        loc = event.get("location", {})
        if loc:
            lines.append(f"   Location: {loc.get('lat', '?')}, {loc.get('lon', '?')}")

        # Parking section
        if parking:
            lines.append(f"\n🅿️ *Parking Nearby:*")
            for p in parking:
                stalli = p.get("stalli", "?")
                lines.append(f"   • {p.get('name', 'Unknown')}: {stalli} spaces")
        else:
            lines.append("\n🅿️ No parking found nearby.")

        # Transit section
        if transit:
            lines.append(f"\n🚌 *Public Transport:*")
            for t in transit:
                stop = t.get("stop_name", "Unknown")
                line_nums = ", ".join(t.get("lines", []))
                lines.append(f"   • {stop}: Lines {line_nums}")
        else:
            lines.append("\n🚌 No transit stops found nearby.")

        return "\n".join(lines)
