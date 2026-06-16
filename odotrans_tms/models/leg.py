# -*- coding: utf-8 -*-
"""Transport leg — one movement segment of a shipment.

A shipment may move through several legs (e.g. first-mile, line-haul,
last-mile, cross-dock). Each leg owns an ordered set of stops and may be
fulfilled by a different trip/vehicle.
"""
from odoo import api, fields, models


class OdotransLeg(models.Model):
    _name = "odotrans.leg"
    _description = "ODOTRANS Transport Leg"
    _order = "shipment_id, sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    shipment_id = fields.Many2one(
        "odotrans.shipment", required=True, ondelete="cascade", index=True,
    )
    company_id = fields.Many2one(related="shipment_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    mode = fields.Selection(
        [("road", "Road"), ("rail", "Rail"), ("air", "Air"), ("sea", "Sea")],
        default="road", required=True,
    )
    stop_ids = fields.One2many("odotrans.stop", "leg_id", string="Stops")
    planned_start = fields.Datetime()
    planned_end = fields.Datetime()
    # Soft link to the fulfilling trip (owned by dispatch context).
    trip_ref = fields.Char(string="Trip Reference", readonly=True, copy=False, index=True)

    @api.depends("shipment_id.name", "sequence")
    def _compute_name(self):
        for leg in self:
            leg.name = f"{leg.shipment_id.name or '?'}/L{leg.sequence}"
