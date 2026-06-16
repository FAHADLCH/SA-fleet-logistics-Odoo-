# -*- coding: utf-8 -*-
"""OSRM adapter — self-hosted routing baseline (cost-free, high throughput).

OSRM provides routing/matrix/trip services but no geocoding; geocoding is
delegated to a configurable Nominatim endpoint. Config keys:

* ``odotrans.map.osrm.base_url``       (e.g. http://osrm:5000)
* ``odotrans.map.osrm.nominatim_url``  (e.g. http://nominatim:8080)
* ``odotrans.map.osrm.profile``        (driving | car | ...)
"""
from odoo import models


def _coords(points):
    # points: iterable of (lat, lng) -> OSRM wants "lng,lat;lng,lat"
    return ";".join(f"{lng},{lat}" for lat, lng in points)


class OdotransProviderOsrm(models.AbstractModel):
    _name = "odotrans.provider.osrm"
    _inherit = "odotrans.map.provider"
    _description = "ODOTRANS Map Provider — OSRM"

    _provider_code = "osrm"

    def _base(self):
        return (self._config("base_url") or "http://localhost:5000").rstrip("/")

    def _profile(self):
        return self._config("profile") or "driving"

    def geocode(self, address):
        base = (self._config("nominatim_url") or "https://nominatim.openstreetmap.org").rstrip("/")
        data = self._request(
            "GET", f"{base}/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "ODOTRANS/1.0"},
        )
        if not data:
            return None
        hit = data[0]
        return {"lat": float(hit["lat"]), "lng": float(hit["lon"]),
                "formatted": hit.get("display_name")}

    def reverse_geocode(self, lat, lng):
        base = (self._config("nominatim_url") or "https://nominatim.openstreetmap.org").rstrip("/")
        data = self._request(
            "GET", f"{base}/reverse",
            params={"lat": lat, "lon": lng, "format": "json"},
            headers={"User-Agent": "ODOTRANS/1.0"},
        )
        return {"address": data.get("display_name")} if data else None

    def distance_matrix(self, origins, destinations):
        points = list(origins) + list(destinations)
        n_orig = len(origins)
        sources = ";".join(str(i) for i in range(n_orig))
        dests = ";".join(str(i) for i in range(n_orig, len(points)))
        url = f"{self._base()}/table/v1/{self._profile()}/{_coords(points)}"
        data = self._request(
            "GET", url,
            params={"sources": sources, "destinations": dests,
                    "annotations": "distance,duration"},
        )
        distances = data.get("distances", [])
        durations = data.get("durations", [])
        matrix = []
        for i in range(len(origins)):
            row = []
            for j in range(len(destinations)):
                row.append((
                    distances[i][j] if distances else None,
                    durations[i][j] if durations else None,
                ))
            matrix.append(row)
        return matrix

    def directions(self, waypoints):
        url = f"{self._base()}/route/v1/{self._profile()}/{_coords(waypoints)}"
        data = self._request("GET", url, params={"overview": "full", "geometries": "polyline"})
        route = (data.get("routes") or [{}])[0]
        return {
            "distance": route.get("distance"),
            "duration": route.get("duration"),
            "geometry": route.get("geometry"),
            "legs": route.get("legs", []),
        }

    def optimize(self, depot, stops, options=None):
        points = [depot] + list(stops)
        url = f"{self._base()}/trip/v1/{self._profile()}/{_coords(points)}"
        data = self._request(
            "GET", url,
            params={"source": "first", "roundtrip": "true",
                    "overview": "full", "geometries": "polyline"},
        )
        trip = (data.get("trips") or [{}])[0]
        sequence = [wp.get("waypoint_index") for wp in data.get("waypoints", [])]
        return {
            "sequence": sequence,
            "geometry": trip.get("geometry"),
            "summary": {"distance": trip.get("distance"), "duration": trip.get("duration")},
        }
