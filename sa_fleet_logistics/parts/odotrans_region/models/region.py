# -*- coding: utf-8 -*-
"""Region profiles for global rollout.

A region bundles the localisation and compliance choices that vary by market:
units, currency, language, tax regime, hours-of-service rules, sustainability
factors and per-region provider overrides. Companies pick a default region; the
rest of the platform reads region-driven settings through this model instead of
hard-coding country logic.
"""
from odoo import api, fields, models


class OdotransRegion(models.Model):
    _name = "odotrans.region"
    _description = "ODOTRANS Region Profile"
    _order = "sequence, name"

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True, help="Short region code, e.g. NA, EU, GCC.")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    country_ids = fields.Many2many("res.country", string="Countries")

    # --- Units & locale ---------------------------------------------------
    measurement_system = fields.Selection(
        [("metric", "Metric (km, kg)"), ("imperial", "Imperial (mi, lb)")],
        default="metric", required=True,
    )
    distance_unit = fields.Selection(
        [("km", "Kilometres"), ("mi", "Miles")], default="km", required=True,
    )
    temperature_unit = fields.Selection(
        [("c", "Celsius"), ("f", "Fahrenheit")], default="c", required=True,
    )
    drive_side = fields.Selection(
        [("right", "Right-hand traffic"), ("left", "Left-hand traffic")], default="right",
    )
    currency_id = fields.Many2one("res.currency", string="Default Currency")
    lang_id = fields.Many2one("res.lang", string="Default Language")
    tz = fields.Selection("_tz_get", string="Timezone")

    # --- Compliance -------------------------------------------------------
    compliance_profile = fields.Selection(
        [
            ("generic", "Generic"),
            ("us_fmcsa", "US — FMCSA HOS / ELD"),
            ("eu_tacho", "EU — Tachograph / Mobility Package"),
            ("gcc", "GCC — Gulf Transport"),
            ("india", "India — AIS-140 / GST E-way"),
        ],
        default="generic", required=True,
    )
    max_driving_hours_day = fields.Float(string="Max Driving / Day (h)", default=11.0)
    max_driving_hours_week = fields.Float(string="Max Driving / Week (h)", default=60.0)
    max_continuous_driving_min = fields.Integer(string="Max Continuous Driving (min)", default=480)
    required_break_min = fields.Integer(string="Required Break (min)", default=30)

    tax_regime = fields.Selection(
        [
            ("generic", "Generic"),
            ("us_sales_tax", "US Sales Tax"),
            ("eu_vat", "EU VAT"),
            ("gcc_vat", "GCC VAT"),
            ("india_gst", "India GST"),
        ],
        default="generic", required=True,
    )

    # --- Provider overrides ----------------------------------------------
    map_provider = fields.Selection(
        [("", "Use global default"), ("osrm", "OSRM"), ("google", "Google"), ("mapbox", "Mapbox")],
        string="Map Provider Override",
    )
    ai_provider = fields.Selection(
        [("", "Use global default"), ("heuristic", "Built-in"), ("openai", "OpenAI"),
         ("azure_openai", "Azure OpenAI")],
        string="AI Provider Override",
    )

    # --- Sustainability ---------------------------------------------------
    emission_factor_kg_per_km = fields.Float(
        string="CO₂ Factor (kg/km)", default=0.62,
        help="Average well-to-wheel CO₂e per vehicle-km used for sustainability reporting.",
    )

    # --- Feature flags ----------------------------------------------------
    enable_customs = fields.Boolean(string="Customs & Cross-Border", default=False)
    enable_hazmat = fields.Boolean(string="Dangerous Goods", default=True)
    enable_cold_chain = fields.Boolean(string="Cold Chain", default=True)
    enable_eld = fields.Boolean(string="ELD / Telematics Mandate", default=False)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Region code must be unique."),
    ]

    @api.model
    def _tz_get(self):
        import pytz
        return [(tz, tz) for tz in sorted(pytz.all_timezones)]

    @api.onchange("measurement_system")
    def _onchange_measurement_system(self):
        if self.measurement_system == "imperial":
            self.distance_unit, self.temperature_unit = "mi", "f"
        else:
            self.distance_unit, self.temperature_unit = "km", "c"

    @api.model
    def for_company(self, company=None):
        """Return the effective region for ``company`` (falls back to the
        first active region, then an empty recordset)."""
        company = company or self.env.company
        region = company.odotrans_region_id
        if region:
            return region
        return self.search([("active", "=", True)], limit=1)

    def convert_distance_km(self, km):
        """Express ``km`` in this region's distance unit."""
        self.ensure_one()
        return km * 0.621371 if self.distance_unit == "mi" else km
