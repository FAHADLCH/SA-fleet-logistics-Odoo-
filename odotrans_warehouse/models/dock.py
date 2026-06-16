# -*- coding: utf-8 -*-
"""Warehouse docks and bays.

A dock is a physical inbound/outbound door tied to an Odoo ``stock.warehouse``.
Docks have a status so the dispatcher/warehouse op can see availability and
schedule appointments. Bays are storage/staging positions within the warehouse
used during cross-dock.
"""
from odoo import fields, models


class OdotransDock(models.Model):
    _name = "odotrans.dock"
    _description = "ODOTRANS Dock"
    _order = "warehouse_id, code"

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True)
    warehouse_id = fields.Many2one("stock.warehouse", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="warehouse_id.company_id", store=True, index=True)
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound"), ("both", "Both")],
        default="both", required=True,
    )
    status = fields.Selection(
        [("free", "Free"), ("occupied", "Occupied"), ("blocked", "Blocked")],
        default="free", index=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique_per_wh", "unique(warehouse_id, code)",
         "Dock code must be unique per warehouse."),
    ]

    def action_occupy(self):
        self.write({"status": "occupied"})

    def action_free(self):
        self.write({"status": "free"})


class OdotransBay(models.Model):
    _name = "odotrans.bay"
    _description = "ODOTRANS Staging Bay"
    _order = "warehouse_id, code"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    warehouse_id = fields.Many2one("stock.warehouse", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="warehouse_id.company_id", store=True, index=True)
    capacity_pallets = fields.Integer(default=0)
    active = fields.Boolean(default=True)
