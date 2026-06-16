# -*- coding: utf-8 -*-
"""Vehicle defects reported by drivers or inspections.

A defect is a lightweight issue report against a vehicle. Severity drives
whether the vehicle should be grounded immediately; converting a defect creates
a corrective work order linked back to the defect for traceability.
"""
from odoo import api, fields, models


class OdotransDefect(models.Model):
    _name = "odotrans.defect"
    _description = "ODOTRANS Vehicle Defect"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle", required=True, ondelete="cascade", index=True,
        domain="[('odotrans_enabled','=',True)]",
    )
    reported_by = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    driver_id = fields.Many2one("odotrans.driver", string="Reporting Driver")
    severity = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium", required=True, index=True, tracking=True,
    )
    description = fields.Text(required=True)
    state = fields.Selection(
        [("open", "Open"), ("in_progress", "In Progress"),
         ("resolved", "Resolved"), ("dismissed", "Dismissed")],
        default="open", required=True, index=True, tracking=True,
    )
    work_order_id = fields.Many2one("odotrans.work.order", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.defect") or "New"
        defects = super().create(vals_list)
        # Critical defects ground the vehicle immediately.
        for defect in defects.filtered(lambda d: d.severity == "critical"):
            defect.env["odotrans.event.bus"].emit(
                topic="maintenance.vehicle_down",
                payload={"vehicle_id": defect.vehicle_id.id, "defect": defect.name,
                         "severity": defect.severity},
                source_model=defect._name, source_res_id=defect.id,
            )
        return defects

    def action_create_work_order(self):
        """Escalate the defect into a corrective work order."""
        self.ensure_one()
        wo = self.env["odotrans.work.order"].create({
            "vehicle_id": self.vehicle_id.id,
            "defect_id": self.id,
            "order_type": "corrective",
            "service_type": "other",
            "name": f"Corrective - {self.vehicle_id.name}",
        })
        self.write({"work_order_id": wo.id, "state": "in_progress"})
        return {
            "type": "ir.actions.act_window",
            "res_model": "odotrans.work.order",
            "res_id": wo.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_resolve(self):
        self.write({"state": "resolved"})

    def action_dismiss(self):
        self.write({"state": "dismissed"})
