# -*- coding: utf-8 -*-
"""Google Maps Platform adapter.

Premium fallback with full geocoding + traffic-aware routing. Config keys:

* ``odotrans.map.google.api_key``
* ``odotrans.map.google.base_url`` (default https://maps.googleapis.com/maps/api)
"""
from odoo import models
from odoo.exceptions import UserError


class OdotransProviderGoogle(models.AbstractModel):
    _name = "odotrans.provider.google"
    _inherit = "odotrans.map.provider"
    _description = "ODOTRANS Map Provider — Google"

    _provider_code = "google"

    def _key(self):
        key = self._config("api_key")
        if not key:
            raise UserError("Google map provider selected but no API key configured.")
        return key

    def _base(self):
        return (self._config("base_url") or "https://maps.googleapis.com/maps/api").rstrip("/")

    def geocode(self, address):
        data = self._request(
            "GET", f"{self._base()}/geocode/json",
            params={"address": address, "key": self._key()},
        )
        results = data.get("results") or []
        if not results:
            return None
        loc = results[0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"],
                "formatted": results[0].get("formatted_address")}

    def reverse_geocode(self, lat, lng):
        data = self._request(
            "GET", f"{self._base()}/geocode/json",
            params={"latlng": f"{lat},{lng}", "key": self._key()},
        )
        results = data.get("results") or []
        return {"address": results[0].get("formatted_address")} if results else None

    def distance_matrix(self, origins, destinations):
        def fmt(points):
            return "|".join(f"{lat},{lng}" for lat, lng in points)

        data = self._request(
            "GET", f"{self._base()}/distancematrix/json",
            params={"origins": fmt(origins), "destinations": fmt(destinations),
                    "key": self._key()},
        )
        matrix = []
        for row in data.get("rows", []):
            out = []
            for el in row.get("elements", []):
                out.append((
                    el.get("distance", {}).get("value"),
                    el.get("duration", {}).get("value"),
                ))
            matrix.append(out)
        return matrix

    def directions(self, waypoints):
        origin, *mids, dest = waypoints
        params = {
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{dest[0]},{dest[1]}",
            "key": self._key(),
        }
        if mids:
            params["waypoints"] = "|".join(f"{lat},{lng}" for lat, lng in mids)
        data = self._request("GET", f"{self._base()}/directions/json", params=params)
        route = (data.get("routes") or [{}])[0]
        legs = route.get("legs", [])
        return {
            "distance": sum(l.get("distance", {}).get("value", 0) for l in legs),
            "duration": sum(l.get("duration", {}).get("value", 0) for l in legs),
            "geometry": route.get("overview_polyline", {}).get("points"),
            "legs": legs,
        }

    def optimize(self, depot, stops, options=None):
        params = {
            "origin": f"{depot[0]},{depot[1]}",
            "destination": f"{depot[0]},{depot[1]}",
            "waypoints": "optimize:true|" + "|".join(f"{lat},{lng}" for lat, lng in stops),
            "key": self._key(),
        }
        data = self._request("GET", f"{self._base()}/directions/json", params=params)
        route = (data.get("routes") or [{}])[0]
        legs = route.get("legs", [])
        return {
            "sequence": route.get("waypoint_order", []),
            "geometry": route.get("overview_polyline", {}).get("points"),
            "summary": {
                "distance": sum(l.get("distance", {}).get("value", 0) for l in legs),
                "duration": sum(l.get("duration", {}).get("value", 0) for l in legs),
            },
        }
