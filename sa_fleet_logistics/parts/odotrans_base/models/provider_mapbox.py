# -*- coding: utf-8 -*-
"""Mapbox adapter.

Strong optimization API and matrix support at predictable pricing. Config keys:

* ``odotrans.map.mapbox.access_token``
* ``odotrans.map.mapbox.base_url`` (default https://api.mapbox.com)
* ``odotrans.map.mapbox.profile``  (mapbox/driving | mapbox/driving-traffic)
"""
from odoo import models
from odoo.exceptions import UserError


def _coords(points):
    # Mapbox wants lng,lat;lng,lat
    return ";".join(f"{lng},{lat}" for lat, lng in points)


class OdotransProviderMapbox(models.AbstractModel):
    _name = "odotrans.provider.mapbox"
    _inherit = "odotrans.map.provider"
    _description = "ODOTRANS Map Provider — Mapbox"

    _provider_code = "mapbox"

    def _token(self):
        token = self._config("access_token")
        if not token:
            raise UserError("Mapbox provider selected but no access token configured.")
        return token

    def _base(self):
        return (self._config("base_url") or "https://api.mapbox.com").rstrip("/")

    def _profile(self):
        return self._config("profile") or "mapbox/driving"

    def geocode(self, address):
        url = f"{self._base()}/geocoding/v5/mapbox.places/{address}.json"
        data = self._request("GET", url, params={"access_token": self._token(), "limit": 1})
        feats = data.get("features") or []
        if not feats:
            return None
        lng, lat = feats[0]["center"]
        return {"lat": lat, "lng": lng, "formatted": feats[0].get("place_name")}

    def reverse_geocode(self, lat, lng):
        url = f"{self._base()}/geocoding/v5/mapbox.places/{lng},{lat}.json"
        data = self._request("GET", url, params={"access_token": self._token(), "limit": 1})
        feats = data.get("features") or []
        return {"address": feats[0].get("place_name")} if feats else None

    def distance_matrix(self, origins, destinations):
        points = list(origins) + list(destinations)
        n_orig = len(origins)
        sources = ";".join(str(i) for i in range(n_orig))
        dests = ";".join(str(i) for i in range(n_orig, len(points)))
        url = f"{self._base()}/directions-matrix/v1/{self._profile()}/{_coords(points)}"
        data = self._request(
            "GET", url,
            params={"access_token": self._token(), "sources": sources,
                    "destinations": dests, "annotations": "distance,duration"},
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
        url = f"{self._base()}/directions/v5/{self._profile()}/{_coords(waypoints)}"
        data = self._request(
            "GET", url,
            params={"access_token": self._token(), "overview": "full", "geometries": "polyline"},
        )
        route = (data.get("routes") or [{}])[0]
        return {
            "distance": route.get("distance"),
            "duration": route.get("duration"),
            "geometry": route.get("geometry"),
            "legs": route.get("legs", []),
        }

    def optimize(self, depot, stops, options=None):
        points = [depot] + list(stops)
        url = f"{self._base()}/optimized-trips/v1/{self._profile()}/{_coords(points)}"
        data = self._request(
            "GET", url,
            params={"access_token": self._token(), "source": "first",
                    "roundtrip": "true", "overview": "full", "geometries": "polyline"},
        )
        trip = (data.get("trips") or [{}])[0]
        sequence = [wp.get("waypoint_index") for wp in data.get("waypoints", [])]
        return {
            "sequence": sequence,
            "geometry": trip.get("geometry"),
            "summary": {"distance": trip.get("distance"), "duration": trip.get("duration")},
        }
