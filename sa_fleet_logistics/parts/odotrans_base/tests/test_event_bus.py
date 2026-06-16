# -*- coding: utf-8 -*-
"""Event bus: emission, wildcard matching, and isolated delivery.

Jobs are normally enqueued (not run inline) under queue_job, so the bus pipeline
(`_dispatch` / `_deliver`) is exercised directly to keep assertions deterministic
without a running worker.
"""
from odoo.tests.common import TransactionCase


class TestEventBus(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Bus = self.env["odotrans.event.bus"]
        self.Sub = self.env["odotrans.event.subscription"]
        self.Event = self.env["odotrans.event"]
        # A handler model that always exists and exposes a no-op handler.
        self.handler_model = "odotrans.event.bus"

    def test_emit_creates_event_record(self):
        event = self.Bus.emit(
            topic="test.topic",
            payload={"a": 1},
            source_model="res.partner",
            source_res_id=self.env.user.partner_id.id,
        )
        self.assertTrue(event.name and event.name != "/")
        self.assertEqual(event.topic, "test.topic")
        self.assertEqual(event.payload, {"a": 1})
        self.assertEqual(event.state, "pending")

    def test_emit_rejects_non_dict_payload(self):
        with self.assertRaises(Exception):
            self.Bus.emit(topic="bad", payload=[1, 2, 3])

    def test_exact_topic_match(self):
        sub = self.Sub.create({
            "name": "exact",
            "topic": "shipment.delivered",
            "handler_model": self.handler_model,
            "handler_method": "_dispatch",
        })
        matched = self.Sub._match("shipment.delivered")
        self.assertIn(sub, matched)
        self.assertFalse(self.Sub._match("shipment.created") & sub)

    def test_wildcard_topic_match(self):
        sub = self.Sub.create({
            "name": "wild",
            "topic": "shipment.*",
            "handler_model": self.handler_model,
            "handler_method": "_dispatch",
        })
        self.assertIn(sub, self.Sub._match("shipment.delivered"))
        self.assertIn(sub, self.Sub._match("shipment.created"))
        self.assertFalse(self.Sub._match("trip.created") & sub)

    def test_dispatch_no_subscriber_marks_event(self):
        event = self.Event.create({"topic": "lonely.topic", "payload": {}})
        self.Bus._dispatch(event.id)
        self.assertEqual(event.state, "no_subscriber")

    def test_dispatch_creates_delivery_and_deliver_runs_handler(self):
        sub = self.Sub.create({
            "name": "probe",
            "topic": "probe.fire",
            "handler_model": "odotrans.event.bus",
            "handler_method": "_odotrans_probe_handler",
        })
        event = self.Bus.emit(topic="probe.fire", payload={"x": 1})
        # Run dispatch + delivery synchronously.
        self.Bus._dispatch(event.id)
        delivery = self.env["odotrans.event.delivery"].search([("event_id", "=", event.id)])
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.subscription_id, sub)
        self.Bus._deliver(delivery.id)
        self.assertEqual(delivery.state, "done")
        self.assertEqual(event.state, "dispatched")

    def test_constrains_rejects_unknown_handler(self):
        with self.assertRaises(Exception):
            self.Sub.create({
                "name": "bad",
                "topic": "x",
                "handler_model": "odotrans.event.bus",
                "handler_method": "_method_that_does_not_exist",
            })
