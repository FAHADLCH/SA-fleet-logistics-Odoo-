# -*- coding: utf-8 -*-
"""Preventive-maintenance plans.

A PM plan attaches a recurring service interval (by distance and/or time) to a
vehicle. A daily cron evaluates plans and raises a work order when a vehicle is
due, so maintenance is scheduled proactively rather than only on breakdown.
"""
from datetime import timedelta

from odoo import api, fields, models


class OdotransPmPlan(models.Model):
    _name = "odotrans.pm.plan"
    _description = "ODOTRANS Preventive Maintenance Plan"
    _order = "vehicle_id, id"

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle", required=True, ondelete="cascade", index=True,
        domain="[('odotrans_enabled','=',True)]",
    )
    service_type = fields.Selection(
        [("oil", "Oil Change"), ("tyres", "Tyres"), ("brakes", "Brakes"),
         ("inspection", "Inspection"), ("other", "Other")],
        default="inspection", required=True,
    )
    interval_km = fields.Float(string="Every (km)", help="0 disables distance trigger.")
    interval_days = fields.Integer(string="Every (days)", help="0 disables time trigger.")
    last_service_odometer = fields.Float(string="Last Service Odometer")
    last_service_date = fields.Date(string="Last Service Date")
    next_due_odometer = fields.Float(compute="_compute_next_due", store=True)
    next_due_date = fields.Date(compute="_compute_next_due", store=True)

    @api.depends("interval_km", "interval_days", "last_service_odometer", "last_service_date")
    def _compute_next_due(self):
        for plan in self:
            plan.next_due_odometer = (
                plan.last_service_odometer + plan.interval_km if plan.interval_km else 0.0
            )
            if plan.interval_days and plan.last_service_date:
                plan.next_due_date = plan.last_service_date + timedelta(days=plan.interval_days)
            else:
                plan.next_due_date = False

    def _is_due(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.interval_km and self.next_due_odometer:
            if (self.vehicle_id.odometer or 0.0) >= self.next_due_odometer:
                return True
        if self.interval_days and self.next_due_date:
            if today >= self.next_due_date:
                return True
        return False

    @api.model
    def cron_generate_due_work_orders(self):
        """Daily: open a work order for each due plan without an open one."""
        WorkOrder = self.env["odotrans.work.order"]
        for plan in self.search([("active", "=", True)]):
            if not plan._is_due():
                continue
            existing = WorkOrder.search_count([
                ("plan_id", "=", plan.id), ("state", "not in", ("done", "cancelled")),
            ])
            if existing:
                continue
            WorkOrder.create({
                "vehicle_id": plan.vehicle_id.id,
                "plan_id": plan.id,
                "order_type": "preventive",
                "service_type": plan.service_type,
                "name": f"{plan.service_type.upper()} - {plan.vehicle_id.name}",
            })
        return True
