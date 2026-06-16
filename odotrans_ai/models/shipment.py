# -*- coding: utf-8 -*-
"""AI enrichment of the shipment aggregate.

Adds predictive fields (ETA, delay risk, dynamic price) computed by the
``odotrans.ai`` façade. Analysis runs synchronously on demand (fast heuristic)
and asynchronously when a shipment is confirmed (via the domain event bus), so
operators always see a relevant, up-to-date risk picture.
"""
from datetime import timedelta

from odoo import api, fields, models

from .ai_provider import haversine_km


class OdotransShipment(models.Model):
    _inherit = "odotrans.shipment"

    company_currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", readonly=True,
    )

    ai_eta = fields.Datetime(string="AI Predicted ETA", readonly=True)
    ai_eta_hours = fields.Float(string="AI Transit (h)", readonly=True)
    ai_distance_km = fields.Float(string="AI Distance (km)", readonly=True)
    ai_delay_risk = fields.Float(string="Delay Risk", readonly=True, aggregator="avg")
    ai_risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")],
        string="Risk Level", readonly=True, index=True,
    )
    ai_price_suggestion = fields.Monetary(
        string="AI Price Suggestion", readonly=True, currency_field="company_currency_id",
    )
    ai_explanation = fields.Text(string="AI Reasoning", readonly=True)
    ai_last_run = fields.Datetime(string="AI Last Analysed", readonly=True)
    ai_insight_count = fields.Integer(compute="_compute_ai_insight_count")

    def _compute_ai_insight_count(self):
        Insight = self.env["odotrans.ai.insight"]
        for ship in self:
            ship.ai_insight_count = Insight.search_count([
                ("res_model", "=", "odotrans.shipment"), ("res_id", "=", ship.id),
            ]) if ship.id else 0

    # --- payload assembly --------------------------------------------------
    def _ai_payload(self):
        self.ensure_one()
        distance = haversine_km(self.origin_lat, self.origin_lng, self.dest_lat, self.dest_lng)
        return {
            "distance_km": distance,
            "service_level": self.service_level,
            "priority": self.priority,
            "weight_kg": self.weight_kg,
            "stop_count": self.stop_count or 2,
            "is_late": self.is_late,
            "origin_lat": self.origin_lat, "origin_lng": self.origin_lng,
            "dest_lat": self.dest_lat, "dest_lng": self.dest_lng,
        }

    # --- public action -----------------------------------------------------
    def action_ai_analyze(self):
        """Run ETA + risk + price inference now and persist insights."""
        AI = self.env["odotrans.ai"]
        Insight = self.env["odotrans.ai.insight"]
        for ship in self:
            payload = ship._ai_payload()
            eta = AI.predict_eta(payload)
            risk = AI.score_risk(payload)
            price = AI.suggest_price(payload)

            eta_dt = fields.Datetime.now() + timedelta(hours=eta.get("eta_hours", 0))
            explanation = "Risk factors: " + (", ".join(risk.get("factors")) or "none")
            ship.write({
                "ai_eta": eta_dt,
                "ai_eta_hours": eta.get("eta_hours", 0),
                "ai_distance_km": eta.get("distance_km", 0),
                "ai_delay_risk": risk.get("score", 0),
                "ai_risk_level": risk.get("level", "low"),
                "ai_price_suggestion": price.get("amount", 0),
                "ai_explanation": explanation,
                "ai_last_run": fields.Datetime.now(),
            })
            Insight.log(ship, "eta", score=eta.get("confidence", 0) * 100,
                        value_text=f"{eta.get('eta_hours', 0)} h / {eta.get('distance_km', 0)} km",
                        payload=eta)
            Insight.log(ship, "risk", score=risk.get("score", 0), level=risk.get("level"),
                        value_text=risk.get("level", "low").title(), explanation=explanation,
                        payload=risk)
            Insight.log(ship, "price", value_text=str(price.get("amount", 0)), payload=price)
        return True

    def action_view_ai_insights(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "AI Insights",
            "res_model": "odotrans.ai.insight",
            "view_mode": "list,form",
            "domain": [("res_model", "=", "odotrans.shipment"), ("res_id", "=", self.id)],
            "context": {"create": False},
        }

    # --- async job ---------------------------------------------------------
    def _ai_run(self):
        return self.action_ai_analyze()

    # --- event handler (subscribed via data record) -----------------------
    @api.model
    def _odotrans_ai_on_confirmed(self, event):
        """When a shipment is confirmed, score it asynchronously."""
        payload = event.payload or {}
        shipment_id = payload.get("id")
        if not shipment_id:
            return
        ship = self.browse(shipment_id).exists()
        if ship:
            ship._enqueue(
                "_ai_run",
                channel="root.odotrans.ai",
                description=f"AI analyse {ship.name}",
                idempotency_key=f"ai:{ship.name}",
            )
