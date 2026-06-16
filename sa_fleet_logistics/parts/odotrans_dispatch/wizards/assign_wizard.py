# -*- coding: utf-8 -*-
"""Wizard to assign a vehicle + driver to one or more trips at once.

Only available (and license-valid) resources are offered, using the domains the
fleet context publishes, so dispatchers cannot double-book a busy vehicle.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OdotransAssignWizard(models.TransientModel):
    _name = "odotrans.assign.wizard"
    _description = "Assign Vehicle & Driver to Trips"

    trip_ids = fields.Many2many("odotrans.trip", string="Trips", required=True)
    vehicle_id = fields.Many2one(
        "fleet.vehicle", string="Vehicle", required=True,
        domain="[('odotrans_enabled','=',True),('odotrans_status','=','available')]",
    )
    driver_id = fields.Many2one(
        "odotrans.driver", string="Driver", required=True,
        domain="[('status','=','available'),('license_valid','=',True)]",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids")
        if active_ids:
            res["trip_ids"] = [(6, 0, active_ids)]
        return res

    def action_assign(self):
        self.ensure_one()
        assignable = self.trip_ids.filtered(lambda t: t.state in ("draft", "assigned"))
        if not assignable:
            raise UserError("None of the selected trips can be assigned.")
        for trip in assignable:
            trip.assign(vehicle_id=self.vehicle_id.id, driver_id=self.driver_id.id)
        return {"type": "ir.actions.act_window_close"}
