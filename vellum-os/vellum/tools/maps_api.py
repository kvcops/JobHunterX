"""
Vellum OS — Geospatial Tool (geopy 2.x + overpy 0.7.x)

Converts a city name to coordinates and queries OpenStreetMap
for tech companies via the Overpass API.
Returns results with confidence scores — OSM is supplementary (0.5).
"""

from __future__ import annotations

from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("maps_api")


async def geocode_location(city: str) -> Optional[dict]:
    """Convert a city name to lat/lon using Nominatim.

    Returns: {"lat": float, "lon": float, "display_name": str} or None.
    """
    import asyncio
    from geopy.geocoders import Nominatim

    def _geocode():
        geolocator = Nominatim(user_agent="vellum-os-career-agent")
        location = geolocator.geocode(city)
        if location:
            return {
                "lat": location.latitude,
                "lon": location.longitude,
                "display_name": location.address,
            }
        return None

    try:
        result = await asyncio.to_thread(_geocode)
        if result:
            log.info("geocode_success", city=city, lat=result["lat"], lon=result["lon"])
        else:
            log.warning("geocode_failed", city=city)
        return result
    except Exception as exc:
        log.error("geocode_error", city=city, error=str(exc))
        return None


async def find_tech_companies(
    lat: float, lon: float, radius_km: float = 20.0
) -> list[dict]:
    """Query OpenStreetMap Overpass API for tech/IT companies near coordinates.

    Queries: office=it, office=company, office=coworking with name tag.
    Returns list of {"name": str, "lat": float, "lon": float, "website": str|None,
                      "source": "osm", "confidence": 0.5}.

    Confidence is 0.5 because OSM coverage for Indian tech companies is uneven.
    """
    import asyncio
    import overpy

    # Build bounding box (approximate)
    delta = radius_km / 111.0  # ~111 km per degree
    south = lat - delta
    north = lat + delta
    west = lon - delta
    east = lon + delta

    query = f"""
    [out:json][timeout:30];
    (
      node["office"~"it|company|coworking"]["name"]({south},{west},{north},{east});
      way["office"~"it|company|coworking"]["name"]({south},{west},{north},{east});
      node["building"="commercial"]["name"]({south},{west},{north},{east});
      way["building"="commercial"]["name"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """

    def _query():
        import requests
        url = "https://overpass-api.de/api/interpreter"
        headers = {
            "User-Agent": "VellumOSCareerAgent/1.0 (contact: vamsi@example.com)",
            "Accept": "application/json"
        }
        res = requests.post(url, data={"data": query}, headers=headers, timeout=30)
        res.raise_for_status()
        api = overpy.Overpass()
        return api.parse_json(res.text)

    try:
        result = await asyncio.to_thread(_query)
    except Exception as exc:
        log.error("overpass_query_error", error=str(exc))
        return []

    companies = []
    seen_names = set()

    for node in result.nodes:
        name = node.tags.get("name", "").strip()
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        companies.append({
            "name": name,
            "lat": float(node.lat),
            "lon": float(node.lon),
            "website": node.tags.get("website") or node.tags.get("contact:website"),
            "source": "osm",
            "confidence": 0.5,
        })

    for way in result.ways:
        name = way.tags.get("name", "").strip()
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())
        # Use center node if available
        center_lat = lat
        center_lon = lon
        if way.nodes:
            center_lat = float(way.nodes[0].lat)
            center_lon = float(way.nodes[0].lon)
        companies.append({
            "name": name,
            "lat": center_lat,
            "lon": center_lon,
            "website": way.tags.get("website") or way.tags.get("contact:website"),
            "source": "osm",
            "confidence": 0.5,
        })

    log.info("osm_companies_found", count=len(companies), radius_km=radius_km)
    return companies
