# -*- coding: utf-8 -*-
"""Driver/carrier pay rules.

A pay rule defines how a payee (driver or carrier partner) earns from executing
a trip. Like rate cards, rules are prioritised and may be scoped to a specific
driver; the first matching rule is applied. The settlement run evaluates these
against completed trips to build pay statement lines.
"""
from odoo import api, fields, models


class OdotransPayRule(models.Model):
    _name = "odotrans.pay.rule"
    _description = "ODOTRANS Pay Rule"
    _order = "sequence, id"

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10, help="Lower = higher priority when several match.")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id, required=True,
    )
    payee_type = fields.Selection(
        [("driver", "Driver"), ("carrier", "Carrier")], default="driver", required=True,
    )
    driver_id = fields.Many2one(
        "odotrans.driver", help="Leave empty to apply to all drivers (fallback rule).",
    )
    # Pay components.
    per_trip = fields.Float(string="Per Trip")
    per_km = fields.Float(string="Per km")
    per_stop = fields.Float(string="Per Stop")
    per_kg = fields.Float(string="Per kg")
    min_amount = fields.Float(string="Minimum Guarantee")

    def _matches(self, trip):
        self.ensure_one()
        if self.payee_type == "driver" and self.driver_id:
            return self.driver_id == trip.driver_id
        return True

    @api.model
    def find_for(self, trip):
        rules = self.search(
            [("active", "=", True), ("company_id", "=", trip.company_id.id)], order="sequence",
        )
        for rule in rules:
            if rule._matches(trip):
                return rule
        return self.browse()

    def compute_pay(self, trip, distance_km=0.0):
        """Return the gross pay for a trip under this rule."""
        self.ensure_one()
        amount = self.per_trip
        amount += self.per_km * (distance_km or 0.0)
        amount += self.per_stop * (trip.stop_count or 0)
        amount += self.per_kg * (trip.total_weight_kg or 0.0)
        if self.min_amount and amount < self.min_amount:
            amount = self.min_amount
        return amount
