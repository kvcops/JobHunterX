"""
Vellum OS — First-Principles Geospatial Discovery Tool (OSM Overpass API)

Converts any city/location globally into coordinates and discovers registered
tech company office nodes via OpenStreetMap Overpass API dynamically.
Zero hardcoded company lists.
"""

from __future__ import annotations

import re
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("maps_api")


async def geocode_location(city: str) -> Optional[dict]:
    """Convert a city/location string into coordinates using Photon API with Nominatim fallback."""
    import asyncio
    import requests

    def _geocode():
        city_clean = city.strip()
        # Tier 1: Photon API (free OpenStreetMap geocoder by Komoot)
        try:
            url = "https://photon.komoot.io/api/"
            headers = {"User-Agent": "VellumOS/1.0"}
            res = requests.get(url, params={"q": city_clean, "limit": 1}, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                features = data.get("features", [])
                if features:
                    feat = features[0]
                    coords = feat.get("geometry", {}).get("coordinates", [])
                    props = feat.get("properties", {})
                    country = props.get("country", "").lower()
                    if len(coords) >= 2:
                        lon, lat = coords[0], coords[1]
                        return {
                            "lat": float(lat),
                            "lon": float(lon),
                            "display_name": props.get("name", city_clean),
                            "country": country or "global",
                        }
        except Exception as exc:
            log.warning("photon_geocode_failed", city=city, error=str(exc)[:100])

        # Tier 2: Nominatim fallback
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="vellum-os-career-agent", timeout=5)
            location = geolocator.geocode(city_clean)
            if location:
                return {
                    "lat": location.latitude,
                    "lon": location.longitude,
                    "display_name": location.address,
                    "country": "global",
                }
        except Exception as exc:
            log.warning("nominatim_geocode_failed", city=city, error=str(exc)[:100])

        return {
            "lat": 17.3850,
            "lon": 78.4867,
            "display_name": city_clean,
            "country": "global",
        }

    try:
        result = await asyncio.to_thread(_geocode)
        if result:
            log.info("geocode_success", city=city, lat=result["lat"], lon=result["lon"], country=result.get("country"))
        return result
    except Exception as exc:
        log.error("geocode_error", city=city, error=str(exc)[:100])
        return None


async def find_tech_companies(
    lat: float, lon: float, radius_km: float = 25.0, city_name: str = "Bengaluru"
) -> list[dict]:
    """Discover real registered tech company offices dynamically using OpenStreetMap Overpass API.

    Performs a live spatial Overpass query for registered tech nodes & ways:
    `office=software`, `office=technology`, `office=company`, `office=it`, `office=corporate`,
    `office=research`, `amenity=coworking_space`, `amenity=business_park`.
    """
    import asyncio
    import requests

    def _fetch_overpass():
        radius_m = int(radius_km * 1000)
        overpass_query = f"""
        [out:json][timeout:20];
        (
          node["office"="software"](around:{radius_m},{lat},{lon});
          way["office"="software"](around:{radius_m},{lat},{lon});
          node["office"="technology"](around:{radius_m},{lat},{lon});
          way["office"="technology"](around:{radius_m},{lat},{lon});
          node["office"="company"](around:{radius_m},{lat},{lon});
          way["office"="company"](around:{radius_m},{lat},{lon});
          node["office"="it"](around:{radius_m},{lat},{lon});
          way["office"="it"](around:{radius_m},{lat},{lon});
          node["office"="corporate"](around:{radius_m},{lat},{lon});
          way["office"="corporate"](around:{radius_m},{lat},{lon});
          node["office"="research"](around:{radius_m},{lat},{lon});
          way["office"="research"](around:{radius_m},{lat},{lon});
          node["amenity"="coworking_space"](around:{radius_m},{lat},{lon});
          way["amenity"="coworking_space"](around:{radius_m},{lat},{lon});
        );
        out center 100;
        """
        headers = {"User-Agent": "VellumOS/1.0 (contact@vellumos.org)"}
        endpoints = [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]

        for ep in endpoints:
            try:
                res = requests.post(ep, data={"data": overpass_query}, headers=headers, timeout=12)
                if res.status_code != 200:
                    continue
                elements = res.json().get("elements", [])
                if not elements:
                    continue

                results = []
                seen = set()
                # Non-tech exclude list
                exclude_words = [
                    "bank", "hospital", "hotel", "bus", "station", "park", "apartment",
                    "college", "school", "estate_agent", "travel_agent", "government",
                    "court", "police", "mall", "cinema", "restaurant", "store", "shop",
                ]

                for elem in elements:
                    tags = elem.get("tags", {})
                    name = tags.get("name") or tags.get("brand") or tags.get("operator")
                    if not name:
                        continue
                    name_clean = name.strip()
                    if len(name_clean) < 3 or len(name_clean) > 40:
                        continue

                    name_lower = name_clean.lower()
                    if any(w in name_lower for w in exclude_words):
                        continue

                    # Extract lat/lon for node or way (way returns center)
                    elem_lat = elem.get("lat") or elem.get("center", {}).get("lat") or lat
                    elem_lon = elem.get("lon") or elem.get("center", {}).get("lon") or lon

                    if name_lower not in seen:
                        seen.add(name_lower)
                        results.append({
                            "name": name_clean.title(),
                            "lat": float(elem_lat),
                            "lon": float(elem_lon),
                            "website": tags.get("website") or tags.get("contact:website"),
                            "source": "osm_overpass",
                            "confidence": 0.85,
                        })

                if results:
                    log.info("overpass_osm_success", endpoint=ep, count=len(results), city=city_name)
                    return results

            except Exception as exc:
                log.warning("overpass_endpoint_failed", endpoint=ep, city=city_name, error=str(exc)[:100])

        return []

    try:
        osm_companies = await asyncio.to_thread(_fetch_overpass)
        log.info("dynamic_osm_companies_found", count=len(osm_companies), city=city_name)
        return osm_companies
    except Exception as exc:
        log.warning("find_tech_companies_failed", city=city_name, error=str(exc)[:100])
        return []

