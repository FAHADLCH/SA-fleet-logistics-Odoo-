# -*- coding: utf-8 -*-
"""Delivery exception — a failed or problematic stop needing resolution.

Drivers raise exceptions (customer absent, refused, damaged, access blocked).
Each exception drives a resolution path: reattempt, return-to-origin (RTO) or
cancel. Raising/​resolving emits events so the shipment can flag itself or be
rescheduled.
"""
from odoo import api, fields, models


class OdotransException(models.Model):
    _name = "odotrans.exception"
    _description = "ODOTRANS Delivery Exception"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    stop_id = fields.Many2one("odotrans.stop", required=True, ondelete="cascade", index=True)
    shipment_id = fields.Many2one(related="stop_id.shipment_id", store=True, index=True)
    trip_ref = fields.Char(index=True)
    driver_id = fields.Many2one("odotrans.driver", index=True)

    reason = fields.Selection(
        [
            ("absent", "Customer Absent"),
            ("refused", "Refused"),
            ("damaged", "Damaged Goods"),
            ("access", "Access Blocked"),
            ("address", "Wrong Address"),
            ("other", "Other"),
        ],
        required=True,
    )
    resolution = fields.Selection(
        [("reattempt", "Reattempt"), ("rto", "Return to Origin"), ("cancel", "Cancel")],
    )
    state = fields.Selection(
        [("open", "Open"), ("resolved", "Resolved")],
        default="open", required=True, tracking=True, index=True,
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.exception") or "New"
        records = super().create(vals_list)
        for exc in records:
            exc.stop_id.write({"state": "failed"})
            if exc.shipment_id and exc.shipment_id.state in ("in_transit",):
                exc.shipment_id.action_flag_exception(reason=exc.reason)
            self.env["odotrans.event.bus"].emit(
                topic="pod.exception_raised",
                payload={"exception_id": exc.id, "shipment_id": exc.shipment_id.id,
                         "reason": exc.reason},
                source_model=self._name, source_res_id=exc.id,
            )
        return records

    def action_resolve(self):
        for exc in self:
            exc.state = "resolved"
            self.env["odotrans.event.bus"].emit(
                topic="pod.exception_resolved",
                payload={"exception_id": exc.id, "shipment_id": exc.shipment_id.id,
                         "resolution": exc.resolution},
                source_model=self._name, source_res_id=exc.id,
            )
        return True
