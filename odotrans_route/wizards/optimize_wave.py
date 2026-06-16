# -*- coding: utf-8 -*-
"""Wizard to optimize a *wave* of trips in one shot.

Each selected trip is optimized as an independent queued run, so a 100-trip
wave fans out across the optimization channel's workers rather than blocking.
"""
from odoo import fields, models
from odoo.exceptions import UserError


class OdotransOptimizeWave(models.TransientModel):
    _name = "odotrans.optimize.wave"
    _description = "Optimize Wave"

    trip_ids = fields.Many2many("odotrans.trip", string="Trips")

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids")
        if active_ids:
            res["trip_ids"] = [(6, 0, active_ids)]
        return res

    def action_optimize_wave(self):
        self.ensure_one()
        trips = self.trip_ids.filtered(lambda t: t.manifest_id and t.manifest_id.line_ids)
        if not trips:
            raise UserError("Selected trips have no stops to optimize.")
        Run = self.env["odotrans.optimization.run"]
        for trip in trips:
            Run.optimize_trip(trip)
        return {"type": "ir.actions.act_window_close"}
