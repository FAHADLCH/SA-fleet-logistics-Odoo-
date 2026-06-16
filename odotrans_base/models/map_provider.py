# -*- coding: utf-8 -*-
"""Map / routing provider abstraction.

Domain code never talks to Google, Mapbox or OSRM directly. It calls the
``odotrans.map`` façade, which resolves the company-configured adapter at
runtime. Swapping providers is a configuration change, not a code change.

Capabilities every adapter must implement:

* ``geocode(address)`` -> {lat, lng, formatted, ...}
* ``reverse_geocode(lat, lng)`` -> {address, ...}
* ``distance_matrix(origins, destinations)`` -> nested list of (dist_m, dur_s)
* ``directions(waypoints)`` -> {distance, duration, geometry, legs}
* ``optimize(depot, stops, options)`` -> {sequence, geometry, summary}
"""
import logging

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15  # seconds

# Provider code -> adapter model. New providers register by extending this map
# in their own module (or by overriding ``_provider_registry``).
PROVIDER_REGISTRY = {
    "osrm": "odotrans.provider.osrm",
    "google": "odotrans.provider.google",
    "mapbox": "odotrans.provider.mapbox",
}


class OdotransMapProvider(models.AbstractModel):
    """Interface + shared HTTP helpers. Concrete adapters inherit this."""

    _name = "odotrans.map.provider"
    _description = "ODOTRANS Map Provider (interface)"

    _provider_code = None  # set by each adapter

    # --- interface (adapters must override) -------------------------------
    def geocode(self, address):
        raise NotImplementedError

    def reverse_geocode(self, lat, lng):
        raise NotImplementedError

    def distance_matrix(self, origins, destinations):
        raise NotImplementedError

    def directions(self, waypoints):
        raise NotImplementedError

    def optimize(self, depot, stops, options=None):
        raise NotImplementedError

    # --- shared helpers ----------------------------------------------------
    def _config(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(
            f"odotrans.map.{self._provider_code}.{key}", default
        )

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            _logger.warning("Map provider %s request failed: %s", self._provider_code, exc)
            raise UserError(f"Map provider error ({self._provider_code}): {exc}") from exc


class OdotransMap(models.AbstractModel):
    """Façade used by all domain code. Delegates to the active adapter."""

    _name = "odotrans.map"
    _description = "ODOTRANS Map Façade"

    @api.model
    def _provider_registry(self):
        return dict(PROVIDER_REGISTRY)

    @api.model
    def _active_adapter(self):
        code = self.env["ir.config_parameter"].sudo().get_param(
            "odotrans.map.provider", "osrm"
        )
        model_name = self._provider_registry().get(code)
        if not model_name or model_name not in self.env:
            raise UserError(
                f"No map adapter registered for provider {code!r}. "
                f"Check the ODOTRANS map settings."
            )
        return self.env[model_name]

    # --- delegated capabilities -------------------------------------------
    @api.model
    def geocode(self, address):
        return self._active_adapter().geocode(address)

    @api.model
    def reverse_geocode(self, lat, lng):
        return self._active_adapter().reverse_geocode(lat, lng)

    @api.model
    def distance_matrix(self, origins, destinations):
        return self._active_adapter().distance_matrix(origins, destinations)

    @api.model
    def directions(self, waypoints):
        return self._active_adapter().directions(waypoints)

    @api.model
    def optimize(self, depot, stops, options=None):
        return self._active_adapter().optimize(depot, stops, options=options)
