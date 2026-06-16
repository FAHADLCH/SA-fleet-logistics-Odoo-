# -*- coding: utf-8 -*-
"""FSM behaviour exercised through the shipment aggregate.

Covers the guard (illegal transitions raise) and the automatic domain-event
emission on a successful transition. queue_job dispatch is left enqueued; we
assert on the persisted ``odotrans.event`` row rather than on side effects.
"""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestShipmentFsm(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "ACME"})
        self.Event = self.env["odotrans.event"]

    def _new_shipment(self):
        return self.env["odotrans.shipment"].create({
            "customer_id": self.partner.id,
            "weight_kg": 10.0,
        })

    def test_sequence_assigned_on_create(self):
        ship = self._new_shipment()
        self.assertNotEqual(ship.name, "New")
        self.assertTrue(ship.name.startswith("SHP/"))

    def test_illegal_transition_raises(self):
        ship = self._new_shipment()
        # draft -> delivered is not allowed.
        with self.assertRaises(UserError):
            ship._transition_to("delivered")

    def test_legal_transition_emits_event(self):
        ship = self._new_shipment()
        before = self.Event.search_count([("topic", "=", "odotrans_shipment.confirmed")])
        ship._transition_to("confirmed")
        self.assertEqual(ship.state, "confirmed")
        after = self.Event.search_count([("topic", "=", "odotrans_shipment.confirmed")])
        self.assertEqual(after, before + 1)
        event = self.Event.search(
            [("topic", "=", "odotrans_shipment.confirmed"),
             ("source_res_id", "=", ship.id)], limit=1,
        )
        self.assertEqual(event.payload.get("to"), "confirmed")
        self.assertEqual(event.payload.get("id"), ship.id)

    def test_transition_to_same_state_is_noop(self):
        ship = self._new_shipment()
        # Already draft; transitioning to draft should not raise or emit.
        before = self.Event.search_count([])
        ship._transition_to("draft")
        self.assertEqual(self.Event.search_count([]), before)

    def test_full_happy_path(self):
        ship = self._new_shipment()
        ship._transition_to("confirmed")
        ship._transition_to("planned")
        ship._transition_to("in_transit")
        ship._transition_to("delivered")
        ship._transition_to("closed")
        self.assertEqual(ship.state, "closed")

    def test_exception_recovery_path(self):
        ship = self._new_shipment()
        ship._transition_to("confirmed")
        ship._transition_to("planned")
        ship._transition_to("in_transit")
        ship._transition_to("exception")
        self.assertEqual(ship.state, "exception")
        # exception -> in_transit is allowed (recovery).
        ship._transition_to("in_transit")
        self.assertEqual(ship.state, "in_transit")
