# -*- coding: utf-8 -*-
"""Stop — a single physical visit (pickup, drop, or cross-dock) on a leg.

Stops carry the geocode, the service time window and the captured actuals
(arrival/departure). The route-optimization context reads stops to build a
VRP problem; the driver app reads them as the manifest; POD writes back here.
"""
from odoo import api, fields, models


class OdotransStop(models.Model):
    _name = "odotrans.stop"
    _description = "ODOTRANS Stop"
    _order = "leg_id, sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    leg_id = fields.Many2one(
        "odotrans.leg", required=True, ondelete="cascade", index=True,
    )
    shipment_id = fields.Many2one(
        related="leg_id.shipment_id", store=True, index=True,
    )
    company_id = fields.Many2one(related="leg_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    stop_type = fields.Selection(
        [("pickup", "Pickup"), ("drop", "Drop"), ("crossdock", "Cross-dock")],
        default="drop", required=True, index=True,
    )
    partner_id = fields.Many2one("res.partner", string="Location Partner")
    lat = fields.Float(digits=(10, 7))
    lng = fields.Float(digits=(10, 7))

    window_start = fields.Datetime(string="Window Start")
    window_end = fields.Datetime(string="Window End")
    service_time_min = fields.Integer(string="Service Time (min)", default=10)

    planned_eta = fields.Datetime(string="Planned ETA")
    actual_arrival = fields.Datetime(readonly=True)
    actual_departure = fields.Datetime(readonly=True)

    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("arrived", "Arrived"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="pending", required=True, index=True,
    )

    @api.depends("leg_id.name", "sequence", "stop_type")
    def _compute_name(self):
        for stop in self:
            stop.name = f"{stop.leg_id.name or '?'}/S{stop.sequence} ({stop.stop_type})"

    def action_mark_arrived(self):
        self.write({"state": "arrived", "actual_arrival": fields.Datetime.now()})

    def action_mark_done(self):
        self.write({"state": "done", "actual_departure": fields.Datetime.now()})
