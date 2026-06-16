# -*- coding: utf-8 -*-
"""Advanced industry capabilities layered onto the core shipment.

Adds the data and behaviour expected of a global 3PL platform: dangerous
goods, cold chain, customs/cross-border, sustainability reporting, reverse
logistics, detention/demurrage, insurance and a public tracking token.
"""
import secrets

from odoo import api, fields, models


class OdotransShipment(models.Model):
    _inherit = "odotrans.shipment"

    adv_currency_id = fields.Many2one(
        "res.currency", string="Currency",
        related="company_id.currency_id", store=True, readonly=True,
    )
    region_id = fields.Many2one(
        "odotrans.region", string="Region", compute="_compute_region_id", store=True,
        help="Region profile driving units, compliance and CO₂ factors.",
    )

    # --- Dangerous goods --------------------------------------------------
    is_hazmat = fields.Boolean(string="Dangerous Goods")
    un_number = fields.Char(string="UN Number")
    hazmat_class = fields.Selection(
        [
            ("1", "1 — Explosives"),
            ("2", "2 — Gases"),
            ("3", "3 — Flammable Liquids"),
            ("4", "4 — Flammable Solids"),
            ("5", "5 — Oxidizers"),
            ("6", "6 — Toxic / Infectious"),
            ("7", "7 — Radioactive"),
            ("8", "8 — Corrosives"),
            ("9", "9 — Miscellaneous"),
        ],
        string="Hazard Class",
    )
    packing_group = fields.Selection(
        [("i", "I — High danger"), ("ii", "II — Medium"), ("iii", "III — Low")],
        string="Packing Group",
    )

    # --- Cold chain -------------------------------------------------------
    temperature_controlled = fields.Boolean(string="Temperature Controlled")
    reefer_required = fields.Boolean(string="Reefer Required")
    temp_min_c = fields.Float(string="Min Temp (°C)")
    temp_max_c = fields.Float(string="Max Temp (°C)")
    temp_last_c = fields.Float(string="Last Reading (°C)")
    temp_breach = fields.Boolean(string="Temperature Breach", compute="_compute_temp_breach", store=True)

    # --- Customs / cross-border ------------------------------------------
    is_cross_border = fields.Boolean(string="Cross-Border")
    incoterm = fields.Selection(
        [
            ("EXW", "EXW — Ex Works"),
            ("FCA", "FCA — Free Carrier"),
            ("CPT", "CPT — Carriage Paid To"),
            ("CIP", "CIP — Carriage & Insurance Paid"),
            ("DAP", "DAP — Delivered At Place"),
            ("DPU", "DPU — Delivered At Place Unloaded"),
            ("DDP", "DDP — Delivered Duty Paid"),
            ("FAS", "FAS — Free Alongside Ship"),
            ("FOB", "FOB — Free On Board"),
            ("CFR", "CFR — Cost & Freight"),
            ("CIF", "CIF — Cost, Insurance & Freight"),
        ],
        string="Incoterm",
    )
    hs_code = fields.Char(string="HS Code")
    customs_value = fields.Monetary(string="Customs Value", currency_field="adv_currency_id")
    country_origin_id = fields.Many2one("res.country", string="Country of Origin")
    country_dest_id = fields.Many2one("res.country", string="Country of Destination")
    customs_status = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("submitted", "Submitted"),
            ("cleared", "Cleared"),
            ("held", "Held"),
        ],
        string="Customs Status", default="not_required",
    )

    # --- Sustainability ---------------------------------------------------
    co2_kg = fields.Float(string="CO₂e (kg)", compute="_compute_co2_kg", store=True)

    # --- Reverse logistics ------------------------------------------------
    is_return = fields.Boolean(string="Return / Reverse")
    return_reason = fields.Selection(
        [
            ("damaged", "Damaged"),
            ("wrong_item", "Wrong Item"),
            ("refused", "Refused by Customer"),
            ("recall", "Recall"),
            ("overstock", "Overstock"),
            ("other", "Other"),
        ],
        string="Return Reason",
    )
    original_shipment_id = fields.Many2one("odotrans.shipment", string="Original Shipment")
    return_shipment_ids = fields.One2many(
        "odotrans.shipment", "original_shipment_id", string="Return Shipments",
    )

    # --- Detention / demurrage -------------------------------------------
    detention_start = fields.Datetime(string="Detention Start")
    detention_end = fields.Datetime(string="Detention End")
    detention_free_min = fields.Integer(string="Free Time (min)", default=120)
    detention_rate_per_hour = fields.Monetary(
        string="Detention Rate / h", currency_field="adv_currency_id",
    )
    detention_minutes = fields.Integer(
        string="Detention (min)", compute="_compute_detention", store=True,
    )
    detention_charge = fields.Monetary(
        string="Detention Charge", currency_field="adv_currency_id",
        compute="_compute_detention", store=True,
    )

    # --- Insurance --------------------------------------------------------
    insured_value = fields.Monetary(string="Insured Value", currency_field="adv_currency_id")
    insurance_policy = fields.Char(string="Insurance Policy")

    # --- Public tracking --------------------------------------------------
    access_token = fields.Char(string="Tracking Token", copy=False, index=True)
    appointment_ids = fields.One2many(
        "odotrans.appointment", "shipment_id", string="Dock Appointments",
    )
    appointment_count = fields.Integer(compute="_compute_appointment_count")

    # ------------------------------------------------------------------ #
    # Computes
    # ------------------------------------------------------------------ #
    @api.depends("company_id")
    def _compute_region_id(self):
        region_model = self.env["odotrans.region"]
        for rec in self:
            rec.region_id = region_model.for_company(rec.company_id)

    @api.depends("temperature_controlled", "temp_last_c", "temp_min_c", "temp_max_c")
    def _compute_temp_breach(self):
        for rec in self:
            breach = False
            if rec.temperature_controlled and (rec.temp_min_c or rec.temp_max_c):
                if rec.temp_last_c < rec.temp_min_c or rec.temp_last_c > rec.temp_max_c:
                    breach = True
            rec.temp_breach = breach

    @api.depends("origin_lat", "origin_lng", "dest_lat", "dest_lng",
                 "region_id", "region_id.emission_factor_kg_per_km")
    def _compute_co2_kg(self):
        for rec in self:
            distance = rec._adv_distance_km()
            factor = rec.region_id.emission_factor_kg_per_km if rec.region_id else 0.62
            rec.co2_kg = round(distance * factor, 2)

    @api.depends("detention_start", "detention_end", "detention_free_min",
                 "detention_rate_per_hour")
    def _compute_detention(self):
        for rec in self:
            minutes = 0
            if rec.detention_start and rec.detention_end and rec.detention_end > rec.detention_start:
                total = (rec.detention_end - rec.detention_start).total_seconds() / 60.0
                minutes = max(0, int(total) - (rec.detention_free_min or 0))
            rec.detention_minutes = minutes
            rec.detention_charge = (minutes / 60.0) * (rec.detention_rate_per_hour or 0.0)

    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = len(rec.appointment_ids)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _adv_distance_km(self):
        """Best-available straight-line distance for CO₂ estimation.

        Reuses the AI distance field when the AI module is installed; otherwise
        falls back to a haversine of the shipment coordinates.
        """
        self.ensure_one()
        ai_distance = getattr(self, "ai_distance_km", 0.0)
        if ai_distance:
            return ai_distance
        if self.origin_lat and self.origin_lng and self.dest_lat and self.dest_lng:
            from math import asin, cos, radians, sin, sqrt
            lat1, lon1, lat2, lon2 = map(
                radians, [self.origin_lat, self.origin_lng, self.dest_lat, self.dest_lng]
            )
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            return 6371.0 * 2 * asin(sqrt(a))
        return 0.0

    def _ensure_access_token(self):
        for rec in self:
            if not rec.access_token:
                rec.access_token = secrets.token_urlsafe(24)
        return self.access_token

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def action_share_tracking(self):
        self.ensure_one()
        self._ensure_access_token()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        url = "%s/odotrans/track/%s" % (base_url, self.access_token)
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_create_return(self):
        self.ensure_one()
        return_shipment = self.copy({
            "is_return": True,
            "original_shipment_id": self.id,
            "origin_partner_id": self.dest_partner_id.id,
            "dest_partner_id": self.origin_partner_id.id,
            "state": "draft",
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "odotrans.shipment",
            "res_id": return_shipment.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_appointments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Dock Appointments",
            "res_model": "odotrans.appointment",
            "view_mode": "list,form",
            "domain": [("shipment_id", "=", self.id)],
            "context": {"default_shipment_id": self.id},
        }
