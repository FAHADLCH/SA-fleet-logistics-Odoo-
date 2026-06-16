# -*- coding: utf-8 -*-
"""Natural-language dispatch assistant (backend wizard)."""
import json

from odoo import fields, models


class OdotransAiAssistant(models.TransientModel):
    _name = "odotrans.ai.assistant"
    _description = "ODOTRANS AI Assistant"

    prompt = fields.Char(string="Ask ODOTRANS AI", required=True)
    answer = fields.Text(readonly=True)
    actions_json = fields.Text(string="Suggested Actions", readonly=True)

    def action_ask(self):
        self.ensure_one()
        result = self.env["odotrans.ai"].assist(self.prompt)
        self.answer = result.get("answer", "")
        actions = result.get("actions") or []
        self.actions_json = json.dumps(actions, indent=2) if actions else False
        return {
            "type": "ir.actions.act_window",
            "res_model": "odotrans.ai.assistant",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
