# -*- coding: utf-8 -*-
"""Map provider configuration exposed in Settings.

Provider selection is stored as a plain ``ir.config_parameter`` so worker
processes (which may run without a UI session) resolve the adapter the same way
the backend does. Credentials are stored under per-provider config keys.
"""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    odotrans_map_provider = fields.Selection(
        [
            ("osrm", "OSRM (self-hosted)"),
            ("google", "Google Maps"),
            ("mapbox", "Mapbox"),
        ],
        string="Map Provider",
        default="osrm",
        config_parameter="odotrans.map.provider",
    )

    # OSRM
    odotrans_osrm_base_url = fields.Char(
        string="OSRM Base URL", config_parameter="odotrans.map.osrm.base_url"
    )
    odotrans_osrm_nominatim_url = fields.Char(
        string="Nominatim URL", config_parameter="odotrans.map.osrm.nominatim_url"
    )

    # Google
    odotrans_google_api_key = fields.Char(
        string="Google API Key", config_parameter="odotrans.map.google.api_key"
    )

    # Mapbox
    odotrans_mapbox_access_token = fields.Char(
        string="Mapbox Access Token", config_parameter="odotrans.map.mapbox.access_token"
    )

    @api.model
    def odotrans_test_provider(self):
        """Smoke-test the configured provider with a known geocode lookup."""
        return self.env["odotrans.map"].geocode("1600 Amphitheatre Parkway, Mountain View, CA")
