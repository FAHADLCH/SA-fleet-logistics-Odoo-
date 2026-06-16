# -*- coding: utf-8 -*-
"""Async dispatch mixin.

Thin, opinionated wrapper over ``queue_job`` so every heavy domain operation
(optimization, rating, settlement, telemetry rollups) is enqueued the same way:
on a named channel, with a human-readable description and an idempotency key
that prevents duplicate work when producers retry.
"""
import hashlib

from odoo import models


class OdotransAsyncMixin(models.AbstractModel):
    _name = "odotrans.async.mixin"
    _description = "ODOTRANS Async Dispatch Mixin"

    # Default channel for this model's background work.
    _odotrans_channel = "root.odotrans.default"

    def _enqueue(self, method_name, *args, channel=None, description=None,
                 idempotency_key=None, **kwargs):
        """Enqueue ``self.method_name(*args, **kwargs)`` as a background job.

        :param idempotency_key: stable string; identical keys collapse to a
            single in-flight job (relies on queue_job ``identity_key``).
        """
        self.ensure_one()
        channel = channel or self._odotrans_channel
        description = description or f"{self._name}.{method_name}({self.id})"
        identity = None
        if idempotency_key:
            digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
            identity = f"{self._name}:{self.id}:{method_name}:{digest}"
        delayed = self.with_delay(
            channel=channel,
            description=description,
            identity_key=identity,
        )
        return getattr(delayed, method_name)(*args, **kwargs)
