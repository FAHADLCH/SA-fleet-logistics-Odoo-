# -*- coding: utf-8 -*-
"""Async mixin: channel defaulting and idempotency-key derivation.

``with_delay`` is patched so no worker is required; we assert the mixin passes
the right channel/description/identity_key and returns the delayed call result.
"""
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestAsyncMixin(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "ACME"})
        self.ship = self.env["odotrans.shipment"].create({
            "customer_id": self.partner.id,
        })

    def test_enqueue_uses_default_channel_and_identity(self):
        captured = {}

        def fake_with_delay(**kwargs):
            captured.update(kwargs)
            stub = MagicMock()
            stub._geocode_endpoints.return_value = "queued"
            return stub

        with patch.object(type(self.ship), "with_delay", side_effect=fake_with_delay):
            result = self.ship._enqueue(
                "_geocode_endpoints",
                channel="root.odotrans.default",
                description="geo",
                idempotency_key="ship-geo-1",
            )

        self.assertEqual(result, "queued")
        self.assertEqual(captured["channel"], "root.odotrans.default")
        self.assertEqual(captured["description"], "geo")
        # identity_key is a stable hash-suffixed string scoped to model+id+method.
        self.assertTrue(captured["identity_key"].startswith(
            f"{self.ship._name}:{self.ship.id}:_geocode_endpoints:"
        ))

    def test_enqueue_without_idempotency_has_no_identity(self):
        captured = {}

        def fake_with_delay(**kwargs):
            captured.update(kwargs)
            return MagicMock()

        with patch.object(type(self.ship), "with_delay", side_effect=fake_with_delay):
            self.ship._enqueue("_geocode_endpoints")

        self.assertIsNone(captured["identity_key"])
        # Falls back to the model's declared default channel.
        self.assertEqual(captured["channel"], "root.odotrans.default")

    def test_same_idempotency_key_yields_same_identity(self):
        keys = []

        def fake_with_delay(**kwargs):
            keys.append(kwargs["identity_key"])
            return MagicMock()

        with patch.object(type(self.ship), "with_delay", side_effect=fake_with_delay):
            self.ship._enqueue("_geocode_endpoints", idempotency_key="same")
            self.ship._enqueue("_geocode_endpoints", idempotency_key="same")

        self.assertEqual(keys[0], keys[1])
