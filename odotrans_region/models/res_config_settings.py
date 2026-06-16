# -*- coding: utf-8 -*-
"""Expose the company's default region in Settings."""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    odotrans_region_id = fields.Many2one(
        "odotrans.region", string="Default Region",
        related="company_id.odotrans_region_id", readonly=False,
    )
