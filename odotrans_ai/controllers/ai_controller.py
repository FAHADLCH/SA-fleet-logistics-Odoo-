# -*- coding: utf-8 -*-
"""JSON endpoint for the AI assistant (mobile / external surfaces)."""
from odoo import http
from odoo.http import request


class OdotransAiController(http.Controller):

    @http.route("/odotrans/api/v1/ai/assistant", type="json", auth="user", methods=["POST"])
    def ai_assistant(self, **kwargs):
        prompt = (kwargs.get("prompt") or "").strip()
        if not prompt:
            return {"error": "prompt is required"}
        return request.env["odotrans.ai"].assist(prompt)
