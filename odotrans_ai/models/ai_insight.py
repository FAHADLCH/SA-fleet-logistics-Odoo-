# -*- coding: utf-8 -*-
"""AI insight — an auditable, explainable record of any AI inference.

Every prediction ODOTRANS makes (ETA, risk, price, anomaly, recommendation) is
persisted as an insight linked to its source record. This keeps the AI
transparent: operators can see what was predicted, when, by which provider, and
the reasoning behind it.
"""
from odoo import api, fields, models


class OdotransAiInsight(models.Model):
    _name = "odotrans.ai.insight"
    _description = "ODOTRANS AI Insight"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, index=True)
    insight_type = fields.Selection(
        [
            ("eta", "ETA Prediction"),
            ("risk", "Delay Risk"),
            ("price", "Price Suggestion"),
            ("anomaly", "Anomaly"),
            ("recommendation", "Recommendation"),
        ],
        required=True, index=True,
    )
    res_model = fields.Char(string="Source Model", index=True)
    res_id = fields.Many2oneReference(string="Source Record", model_field="res_model", index=True)
    score = fields.Float(help="Normalised 0-100 score where applicable.")
    level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")], index=True,
    )
    value_text = fields.Char(string="Summary")
    explanation = fields.Text()
    payload = fields.Json()
    provider = fields.Char(readonly=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True,
    )

    @api.model
    def log(self, record, insight_type, score=0.0, level=False, value_text=False,
            explanation=False, payload=None):
        """Create an insight for ``record``. Returns the new insight."""
        provider = self.env["ir.config_parameter"].sudo().get_param(
            "odotrans.ai.provider", "heuristic"
        )
        return self.create({
            "name": f"{insight_type.upper()} · {record.display_name}",
            "insight_type": insight_type,
            "res_model": record._name,
            "res_id": record.id,
            "score": score,
            "level": level or False,
            "value_text": value_text or False,
            "explanation": explanation or False,
            "payload": payload or {},
            "provider": provider,
        })
