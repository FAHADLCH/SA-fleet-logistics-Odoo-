# -*- coding: utf-8 -*-
"""Billing-side extension of the shipment: the charge backlink + status."""
from odoo import api, fields, models


class OdotransShipment(models.Model):
    _inherit = "odotrans.shipment"

    charge_ids = fields.One2many("odotrans.charge", "shipment_id", string="Charges")
    charge_total = fields.Monetary(
        compute="_compute_charge_total", store=True, currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        related="company_id.currency_id", store=True, readonly=True,
    )
    billing_state = fields.Selection(
        [("nothing", "Nothing to Bill"), ("to_invoice", "To Invoice"),
         ("invoiced", "Invoiced")],
        compute="_compute_billing_state", store=True, index=True,
    )

    @api.depends("charge_ids.amount", "charge_ids.state")
    def _compute_charge_total(self):
        for ship in self:
            ship.charge_total = sum(
                ship.charge_ids.filtered(lambda c: c.state != "cancelled").mapped("amount")
            )

    @api.depends("charge_ids.state")
    def _compute_billing_state(self):
        for ship in self:
            active = ship.charge_ids.filtered(lambda c: c.state != "cancelled")
            if not active:
                ship.billing_state = "nothing"
            elif all(c.state == "invoiced" for c in active):
                ship.billing_state = "invoiced"
            else:
                ship.billing_state = "to_invoice"
