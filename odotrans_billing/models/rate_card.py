# -*- coding: utf-8 -*-
"""Rate cards — the pricing rules the rating engine applies to a shipment.

A rate card is a prioritised set of rules scoped (optionally) to a customer and
service level. Each rule computes a charge from a base + per-km + per-kg formula
with optional min/max. The engine picks the best-matching active card and
produces ``odotrans.charge`` lines, which later roll up into an Odoo invoice.
"""
from odoo import api, fields, models


class OdotransRateCard(models.Model):
    _name = "odotrans.rate.card"
    _description = "ODOTRANS Rate Card"
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
    customer_id = fields.Many2one(
        "res.partner", string="Customer", help="Leave empty for a default/fallback card.",
    )
    service_level = fields.Selection(
        [("any", "Any"), ("economy", "Economy"), ("standard", "Standard"),
         ("express", "Express"), ("same_day", "Same Day")],
        default="any", required=True,
    )
    line_ids = fields.One2many("odotrans.rate.card.line", "card_id", string="Rules")
    valid_from = fields.Date()
    valid_to = fields.Date()

    def _matches(self, shipment):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_to and today > self.valid_to:
            return False
        if self.customer_id and self.customer_id != shipment.customer_id:
            return False
        if self.service_level != "any" and self.service_level != shipment.service_level:
            return False
        return True

    @api.model
    def find_for(self, shipment):
        """Return the best (lowest-sequence) active card matching the shipment."""
        cards = self.search([("active", "=", True),
                             ("company_id", "=", shipment.company_id.id)], order="sequence")
        for card in cards:
            if card._matches(shipment):
                return card
        return self.browse()

    def rate(self, shipment, distance_km=0.0):
        """Compute charge value dicts (not persisted) for a shipment."""
        self.ensure_one()
        charges = []
        for line in self.line_ids:
            amount = line._compute_amount(shipment, distance_km)
            if amount:
                charges.append({
                    "card_line_id": line.id,
                    "charge_type": line.charge_type,
                    "name": line.name,
                    "amount": amount,
                })
        return charges


class OdotransRateCardLine(models.Model):
    _name = "odotrans.rate.card.line"
    _description = "ODOTRANS Rate Card Rule"
    _order = "card_id, sequence, id"

    card_id = fields.Many2one("odotrans.rate.card", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    charge_type = fields.Selection(
        [("freight", "Freight"), ("fuel", "Fuel Surcharge"),
         ("handling", "Handling"), ("accessorial", "Accessorial")],
        default="freight", required=True,
    )
    base_amount = fields.Float(string="Base")
    per_km = fields.Float(string="Per km")
    per_kg = fields.Float(string="Per kg")
    min_amount = fields.Float(string="Minimum")
    max_amount = fields.Float(string="Maximum")

    def _compute_amount(self, shipment, distance_km):
        self.ensure_one()
        amount = self.base_amount
        amount += self.per_km * (distance_km or 0.0)
        amount += self.per_kg * (shipment.weight_kg or 0.0)
        if self.min_amount and amount < self.min_amount:
            amount = self.min_amount
        if self.max_amount and amount > self.max_amount:
            amount = self.max_amount
        return amount
