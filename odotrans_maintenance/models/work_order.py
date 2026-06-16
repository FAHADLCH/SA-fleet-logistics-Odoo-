# -*- coding: utf-8 -*-
"""Work orders — the maintenance execution aggregate.

A work order tracks a single maintenance job on a vehicle from request through
completion. Putting a work order *in progress* takes the vehicle out of the
dispatchable pool by emitting ``maintenance.vehicle_down`` (the fleet context
subscribes and flags the vehicle). Completion restores availability and updates
the originating PM plan's last-service markers so the next interval is computed.
"""
from odoo import api, fields, models


class OdotransWorkOrder(models.Model):
    _name = "odotrans.work.order"
    _description = "ODOTRANS Work Order"
    _inherit = ["odotrans.state.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    _odotrans_state_field = "state"
    _odotrans_transitions = {
        "draft": ["in_progress", "cancelled"],
        "in_progress": ["done", "cancelled"],
        "done": [],
    }

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle", required=True, ondelete="cascade", index=True,
        domain="[('odotrans_enabled','=',True)]", tracking=True,
    )
    plan_id = fields.Many2one("odotrans.pm.plan", string="PM Plan", ondelete="set null")
    defect_id = fields.Many2one("odotrans.defect", string="Source Defect", ondelete="set null")
    order_type = fields.Selection(
        [("preventive", "Preventive"), ("corrective", "Corrective")],
        default="corrective", required=True, index=True,
    )
    service_type = fields.Selection(
        [("oil", "Oil Change"), ("tyres", "Tyres"), ("brakes", "Brakes"),
         ("inspection", "Inspection"), ("other", "Other")],
        default="inspection", required=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In Progress"),
         ("done", "Done"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True, index=True,
    )
    scheduled_date = fields.Date(default=fields.Date.context_today)
    started_at = fields.Datetime(readonly=True)
    completed_at = fields.Datetime(readonly=True)
    odometer = fields.Float(string="Odometer at Service")
    cost = fields.Monetary()
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id, required=True,
    )
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.work.order") or "New"
        return super().create(vals_list)

    def action_start(self):
        """Begin work and take the vehicle out of the dispatch pool."""
        for wo in self:
            wo.write({"started_at": fields.Datetime.now()})
            wo._transition_to("in_progress")
            wo.env["odotrans.event.bus"].emit(
                topic="maintenance.vehicle_down",
                payload={"vehicle_id": wo.vehicle_id.id, "work_order": wo.name,
                         "service_type": wo.service_type},
                source_model=wo._name, source_res_id=wo.id,
            )
        return True

    def action_done(self):
        """Complete work, refresh the PM plan and return the vehicle to service."""
        for wo in self:
            wo.write({"completed_at": fields.Datetime.now()})
            if not wo.odometer:
                wo.odometer = wo.vehicle_id.odometer
            wo._transition_to("done")
            if wo.plan_id:
                wo.plan_id.write({
                    "last_service_odometer": wo.odometer,
                    "last_service_date": fields.Date.context_today(wo),
                })
            wo.env["odotrans.event.bus"].emit(
                topic="maintenance.vehicle_up",
                payload={"vehicle_id": wo.vehicle_id.id, "work_order": wo.name},
                source_model=wo._name, source_res_id=wo.id,
            )
            # No other open work order? restore availability directly.
            others = self.search_count([
                ("vehicle_id", "=", wo.vehicle_id.id),
                ("state", "in", ("draft", "in_progress")),
                ("id", "!=", wo.id),
            ])
            if not others and wo.vehicle_id.odotrans_status == "maintenance":
                wo.vehicle_id.write({"odotrans_status": "available"})
        return True

    def action_cancel(self):
        for wo in self:
            wo._transition_to("cancelled")
        return True
