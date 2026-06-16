# -*- coding: utf-8 -*-
"""Attach a default region to companies."""
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    odotrans_region_id = fields.Many2one(
        "odotrans.region", string="ODOTRANS Region",
        help="Drives units, compliance, tax regime and provider overrides for this company.",
    )
