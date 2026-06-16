# -*- coding: utf-8 -*-
"""Outbound webhook endpoints.

Operators register HTTP endpoints and a topic filter. When ODOTRANS emits a
matching event, every active endpoint receives an asynchronous, HMAC-signed
POST. Delivery runs on the queue_job bus so a slow or unreachable partner never
blocks the originating operation.
"""
import hashlib
import hmac
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OdotransWebhookEndpoint(models.Model):
    _name = "odotrans.webhook.endpoint"
    _description = "ODOTRANS Webhook Endpoint"
    _order = "name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    url = fields.Char(string="Target URL", required=True, tracking=True)
    topic_filter = fields.Char(
        string="Topic Filter", default="odotrans_shipment.*",
        help="Match emitted topics. Supports a single trailing wildcard, "
             "e.g. 'odotrans_shipment.*'. Leave '*' to receive everything.",
    )
    secret = fields.Char(
        string="Signing Secret",
        help="Used to compute the X-Odotrans-Signature HMAC-SHA256 header.",
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True,
    )
    delivery_count = fields.Integer(string="Deliveries", readonly=True, default=0)
    failure_count = fields.Integer(string="Failures", readonly=True, default=0)
    last_status = fields.Char(readonly=True)
    last_delivery = fields.Datetime(readonly=True)

    # ------------------------------------------------------------------ #
    # Matching
    # ------------------------------------------------------------------ #
    def _topic_matches(self, topic):
        self.ensure_one()
        pattern = (self.topic_filter or "*").strip()
        if pattern in ("*", ""):
            return True
        if pattern.endswith(".*"):
            return topic.startswith(pattern[:-1])  # keep the trailing dot
        return topic == pattern

    # ------------------------------------------------------------------ #
    # Event handler (invoked by the event bus, model-level)
    # ------------------------------------------------------------------ #
    @api.model
    def _odotrans_on_event(self, event):
        """Fan an emitted event out to every matching active endpoint."""
        topic = event.topic
        endpoints = self.search([("active", "=", True)]).filtered(
            lambda e: e._topic_matches(topic)
        )
        for endpoint in endpoints:
            endpoint.with_delay(
                channel="root.odotrans.notify",
                description="Webhook %s -> %s" % (topic, endpoint.name),
                identity_key="webhook-%s-%s" % (endpoint.id, event.id),
            )._post(topic, event.payload)
        return True

    # ------------------------------------------------------------------ #
    # Delivery
    # ------------------------------------------------------------------ #
    def _sign(self, body_bytes):
        self.ensure_one()
        if not self.secret:
            return ""
        return hmac.new(
            self.secret.encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()

    def _post(self, topic, payload):
        """Deliver a single webhook. Retried by queue_job on failure."""
        self.ensure_one()
        body = json.dumps(
            {"topic": topic, "payload": payload, "sent_at": fields.Datetime.now().isoformat()},
            default=str,
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Odotrans-Topic": topic,
            "X-Odotrans-Signature": self._sign(body),
        }
        try:
            import requests
            response = requests.post(self.url, data=body, headers=headers, timeout=15)
            ok = response.status_code < 400
            self.sudo().write({
                "delivery_count": self.delivery_count + 1,
                "failure_count": self.failure_count + (0 if ok else 1),
                "last_status": "HTTP %s" % response.status_code,
                "last_delivery": fields.Datetime.now(),
            })
            if not ok:
                raise ValueError("Webhook %s returned HTTP %s" % (self.url, response.status_code))
        except Exception as exc:  # noqa: BLE001 - surfaced to queue_job for retry
            self.sudo().write({
                "failure_count": self.failure_count + 1,
                "last_status": str(exc)[:200],
                "last_delivery": fields.Datetime.now(),
            })
            raise

    def action_send_test(self):
        """Send a synthetic ping so operators can verify the endpoint."""
        self.ensure_one()
        self._post("odotrans.webhook.test", {"message": "ODOTRANS webhook test", "endpoint": self.name})
        return True
