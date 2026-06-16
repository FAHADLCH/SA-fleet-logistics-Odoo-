# -*- coding: utf-8 -*-
"""Billing: rate-card selection, charge computation, and invoicing.

Exercised directly (not via the event handler) so the rating engine is tested in
isolation; a separate assertion confirms the handler is idempotent.
"""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestRating(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "ACME"})
        self.Card = self.env["odotrans.rate.card"]
        self.Charge = self.env["odotrans.charge"]
        self.ship = self.env["odotrans.shipment"].create({
            "customer_id": self.partner.id,
            "service_level": "express",
            "weight_kg": 100.0,
        })

    def _make_card(self, **kw):
        vals = {
            "name": "Default",
            "line_ids": [(0, 0, {
                "name": "Freight",
                "charge_type": "freight",
                "base_amount": 50.0,
                "per_km": 1.0,
                "per_kg": 0.5,
            })],
        }
        vals.update(kw)
        return self.Card.create(vals)

    def test_card_matching_prefers_lower_sequence(self):
        self._make_card(name="generic", sequence=20)
        specific = self._make_card(name="acme-express", sequence=5,
                                   customer_id=self.partner.id, service_level="express")
        found = self.Card.find_for(self.ship)
        self.assertEqual(found, specific)

    def test_card_service_level_filter(self):
        self._make_card(name="economy-only", service_level="economy")
        # No matching card for an express shipment with only an economy card.
        self.assertFalse(self.Card.find_for(self.ship))

    def test_rate_computes_base_plus_km_plus_kg(self):
        card = self._make_card()
        # base 50 + per_km 1*10 + per_kg 0.5*100 = 110
        charges = self.Charge.rate_shipment(self.ship, distance_km=10.0)
        self.assertEqual(len(charges), 1)
        self.assertAlmostEqual(charges.amount, 110.0, places=2)

    def test_min_amount_floor_applied(self):
        self.Card.create({
            "name": "min-floor",
            "line_ids": [(0, 0, {
                "name": "Min", "charge_type": "freight",
                "base_amount": 5.0, "min_amount": 80.0,
            })],
        })
        charges = self.Charge.rate_shipment(self.ship, distance_km=0.0)
        self.assertAlmostEqual(charges.amount, 80.0, places=2)

    def test_rating_is_idempotent(self):
        self._make_card()
        first = self.Charge.rate_shipment(self.ship, distance_km=10.0)
        second = self.Charge.rate_shipment(self.ship, distance_km=10.0)
        self.assertEqual(first, second)
        self.assertEqual(
            self.Charge.search_count([("shipment_id", "=", self.ship.id)]), 1,
        )

    def test_create_invoice_groups_by_customer(self):
        self._make_card()
        charges = self.Charge.rate_shipment(self.ship, distance_km=10.0)
        moves = charges.action_create_invoice()
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves.move_type, "out_invoice")
        self.assertEqual(moves.partner_id, self.partner)
        self.assertEqual(charges.state, "invoiced")
        self.assertEqual(charges.move_id, moves)

    def test_invoice_without_charges_raises(self):
        with self.assertRaises(UserError):
            self.Charge.browse().action_create_invoice()

    def test_event_handler_rates_and_invoices(self):
        self._make_card()
        # Simulate the delivered event payload shape ({"id": shipment_id, ...}).
        fake_event = self.env["odotrans.event"].create({
            "topic": "odotrans_shipment.delivered",
            "payload": {"id": self.ship.id, "to": "delivered"},
            "source_model": "odotrans.shipment",
            "source_res_id": self.ship.id,
        })
        self.Charge._odotrans_on_shipment_delivered(fake_event)
        charges = self.Charge.search([("shipment_id", "=", self.ship.id)])
        self.assertTrue(charges)
        self.assertEqual(charges.mapped("state"), ["invoiced"] * len(charges))
