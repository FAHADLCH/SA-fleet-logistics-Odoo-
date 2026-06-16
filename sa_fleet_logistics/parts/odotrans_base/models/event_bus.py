# -*- coding: utf-8 -*-
"""Asynchronous domain event bus.

ODOTRANS bounded contexts must never write into each other's tables. They
integrate by publishing *domain events* onto this bus. Subscribers are declared
explicitly (data-driven, inspectable) and each delivery runs as an isolated,
retryable ``queue_job`` so a slow or failing consumer never blocks the producer.

Usage (producer)::

    self.env["odotrans.event.bus"].emit(
        topic="shipment.delivered",
        payload={"shipment_id": self.id, "ref": self.name},
        source_model=self._name,
        source_res_id=self.id,
    )

Usage (consumer) — declare a subscription record and implement the handler::

    def _odotrans_on_event(self, event):
        # event is an ``odotrans.event`` recordset (singleton)
        ...
"""
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OdotransEvent(models.Model):
    """Immutable record of a published domain event (audit + replay)."""

    _name = "odotrans.event"
    _description = "ODOTRANS Domain Event"
    _order = "id desc"

    name = fields.Char(string="Reference", required=True, readonly=True, copy=False, index=True)
    topic = fields.Char(required=True, readonly=True, index=True)
    payload = fields.Json(required=True, readonly=True)
    source_model = fields.Char(readonly=True, index=True)
    source_res_id = fields.Many2oneReference(
        string="Source Record", model_field="source_model", readonly=True
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, readonly=True, index=True
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("dispatched", "Dispatched"),
            ("no_subscriber", "No Subscriber"),
        ],
        default="pending",
        readonly=True,
        index=True,
    )
    delivery_ids = fields.One2many(
        "odotrans.event.delivery", "event_id", string="Deliveries", readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name"):
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.event") or "/"
        return super().create(vals_list)


class OdotransEventDelivery(models.Model):
    """Per-subscriber delivery attempt — gives retry/idempotency visibility."""

    _name = "odotrans.event.delivery"
    _description = "ODOTRANS Event Delivery"
    _order = "id desc"

    event_id = fields.Many2one("odotrans.event", required=True, ondelete="cascade", index=True)
    topic = fields.Char(related="event_id.topic", store=True, index=True)
    subscription_id = fields.Many2one(
        "odotrans.event.subscription", required=True, ondelete="cascade", index=True
    )
    handler_model = fields.Char(readonly=True)
    handler_method = fields.Char(readonly=True)
    state = fields.Selection(
        [("queued", "Queued"), ("done", "Done"), ("failed", "Failed")],
        default="queued",
        readonly=True,
        index=True,
    )
    error = fields.Text(readonly=True)


class OdotransEventSubscription(models.Model):
    """Explicit topic -> handler binding. Declared via data records per addon."""

    _name = "odotrans.event.subscription"
    _description = "ODOTRANS Event Subscription"

    name = fields.Char(required=True)
    topic = fields.Char(
        required=True,
        index=True,
        help="Exact topic (shipment.delivered) or wildcard prefix (shipment.*).",
    )
    handler_model = fields.Char(required=True, help="Model exposing the handler method.")
    handler_method = fields.Char(
        required=True,
        default="_odotrans_on_event",
        help="Method called as handler(event). Receives an odotrans.event singleton.",
    )
    channel = fields.Char(
        default="root.odotrans.events",
        help="queue_job channel used for this subscriber's deliveries.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "unique_binding",
            "unique(topic, handler_model, handler_method)",
            "A subscription for this topic/handler already exists.",
        )
    ]

    @api.constrains("handler_model", "handler_method")
    def _check_handler(self):
        for sub in self:
            model = self.env.get(sub.handler_model)
            if model is None:
                raise ValidationError(f"Unknown handler model: {sub.handler_model}")
            if not hasattr(model, sub.handler_method):
                raise ValidationError(
                    f"{sub.handler_model} has no method {sub.handler_method}"
                )

    @api.model
    def _match(self, topic):
        """Return active subscriptions whose topic matches ``topic``."""
        subs = self.search([("active", "=", True)])
        matched = self.browse()
        for sub in subs:
            pattern = sub.topic
            if pattern == topic:
                matched |= sub
            elif pattern.endswith(".*") and topic.startswith(pattern[:-1]):
                matched |= sub
        return matched


class OdotransEventBus(models.AbstractModel):
    """Façade used by producers and the async dispatch pipeline."""

    _name = "odotrans.event.bus"
    _description = "ODOTRANS Event Bus"

    @api.model
    def emit(self, topic, payload, source_model=False, source_res_id=False):
        """Publish a domain event. Fan-out happens asynchronously."""
        if not isinstance(payload, dict):
            raise ValidationError("Event payload must be a JSON-serialisable dict.")
        event = self.env["odotrans.event"].create(
            {
                "topic": topic,
                "payload": payload,
                "source_model": source_model or False,
                "source_res_id": source_res_id or False,
            }
        )
        event.with_delay(
            channel="root.odotrans.events",
            description=f"Dispatch event {topic}",
        )._dispatch(event.id)
        return event

    @api.model
    def _dispatch(self, event_id):
        """Fan an event out to each matching subscriber as an isolated job."""
        event = self.env["odotrans.event"].browse(event_id).exists()
        if not event:
            return
        subscriptions = self.env["odotrans.event.subscription"]._match(event.topic)
        if not subscriptions:
            event.state = "no_subscriber"
            _logger.info("ODOTRANS event %s has no subscriber", event.topic)
            return
        Delivery = self.env["odotrans.event.delivery"]
        for sub in subscriptions:
            delivery = Delivery.create(
                {
                    "event_id": event.id,
                    "subscription_id": sub.id,
                    "handler_model": sub.handler_model,
                    "handler_method": sub.handler_method,
                }
            )
            self.with_delay(
                channel=sub.channel or "root.odotrans.events",
                description=f"Deliver {event.topic} -> {sub.handler_model}",
            )._deliver(delivery.id)
        event.state = "dispatched"

    @api.model
    def _deliver(self, delivery_id):
        """Invoke a single subscriber handler. Idempotent and retryable."""
        delivery = self.env["odotrans.event.delivery"].browse(delivery_id).exists()
        if not delivery or delivery.state == "done":
            return
        try:
            handler = getattr(self.env[delivery.handler_model], delivery.handler_method)
            handler(delivery.event_id)
            delivery.write({"state": "done", "error": False})
        except Exception as exc:  # noqa: BLE001 - surfaced to queue_job for retry
            delivery.write({"state": "failed", "error": str(exc)})
            raise

    @api.model
    def _odotrans_probe_handler(self, event):
        """No-op handler used for health checks and integration tests.

        Lets operators wire a throwaway subscription to verify the full
        emit -> dispatch -> deliver pipeline end to end without side effects.
        """
        return True
