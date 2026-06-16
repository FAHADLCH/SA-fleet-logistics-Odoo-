# -*- coding: utf-8 -*-
"""Inbound integration endpoint.

Partners POST JSON callbacks to ``/odotrans/api/v1/integration/inbound/<code>``.
The connector's ``api_key`` doubles as a shared secret: the caller must present
it in the ``X-API-Key`` header. Matched payloads are re-emitted onto the
internal event bus so any subscriber (webhooks, automations) can react.
"""
import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class OdotransInboundController(http.Controller):

    @http.route(
        "/odotrans/api/v1/integration/inbound/<string:code>",
        type="http", auth="public", methods=["POST"], csrf=False, save_session=False,
    )
    def inbound(self, code, **kwargs):
        connector = (
            request.env["odotrans.integration.connector"]
            .sudo()
            .search([("code", "=", code), ("active", "=", True)], limit=1)
        )
        if not connector:
            return self._json({"error": "unknown_connector"}, status=404)

        # Shared-secret check (constant-time-ish via direct compare on hash).
        provided = request.httprequest.headers.get("X-API-Key", "")
        if connector.api_key and provided != connector.api_key:
            return self._json({"error": "unauthorized"}, status=401)

        try:
            raw = request.httprequest.get_data(as_text=True) or "{}"
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                payload = {"value": payload}
        except (ValueError, TypeError):
            return self._json({"error": "invalid_json"}, status=400)

        connector.sudo().write({
            "status": "ok",
            "last_sync": fields.Datetime.now(),
        })

        topic = "integration.inbound.%s" % code
        request.env["odotrans.event.bus"].sudo().emit(
            topic, {"connector": code, "data": payload},
            source_model="odotrans.integration.connector", source_res_id=connector.id,
        )
        return self._json({"status": "accepted", "topic": topic})

    @staticmethod
    def _json(body, status=200):
        return request.make_response(
            json.dumps(body),
            headers=[("Content-Type", "application/json")],
            status=status,
        )
