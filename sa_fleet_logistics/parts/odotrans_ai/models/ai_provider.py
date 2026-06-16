# -*- coding: utf-8 -*-
"""AI provider abstraction.

Mirrors the map-provider pattern: domain code never calls OpenAI/Azure
directly. It calls the ``odotrans.ai`` façade, which resolves the
company-configured adapter at runtime. The default ``heuristic`` adapter is a
pure-Python, deterministic engine that runs offline (no API key, no network),
so every AI feature works out of the box in demo and degrades gracefully when
an LLM is unavailable.

Tasks every adapter understands (``infer(task, payload)``):

* ``eta``       -> {eta_hours, confidence}
* ``risk``      -> {score, level, factors}
* ``price``     -> {amount, currency, breakdown}
* ``anomaly``   -> {anomalies: [...], score}
* ``assistant`` -> {answer, actions}
* ``document``  -> {fields: {...}, confidence}
"""
import json
import logging
import math
from datetime import datetime

import requests

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds

# Provider code -> adapter model.
AI_PROVIDER_REGISTRY = {
    "heuristic": "odotrans.ai.provider.heuristic",
    "openai": "odotrans.ai.provider.openai",
    "azure_openai": "odotrans.ai.provider.azure",
}

# Average road speed (km/h) assumed per service level for ETA estimation.
_SERVICE_SPEED_KMH = {
    "economy": 45.0,
    "standard": 55.0,
    "express": 65.0,
    "same_day": 38.0,
}


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km between two lat/lng points."""
    if None in (lat1, lng1, lat2, lng2):
        return 0.0
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class OdotransAiProvider(models.AbstractModel):
    """Interface + shared helpers. Concrete adapters inherit this."""

    _name = "odotrans.ai.provider"
    _description = "ODOTRANS AI Provider (interface)"

    _provider_code = None

    def infer(self, task, payload, **opts):
        raise NotImplementedError

    def _config(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(
            f"odotrans.ai.{self._provider_code}.{key}", default
        )

    def _request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            _logger.warning("AI provider %s request failed: %s", self._provider_code, exc)
            raise UserError(f"AI provider error ({self._provider_code}): {exc}") from exc


class OdotransAiProviderHeuristic(models.AbstractModel):
    """Deterministic, offline AI engine — the always-available baseline.

    Uses transparent, explainable rules so predictions are reproducible and
    never depend on an external service. LLM adapters inherit this and override
    only the language tasks (assistant, document).
    """

    _name = "odotrans.ai.provider.heuristic"
    _description = "ODOTRANS AI Provider (heuristic)"
    _inherit = "odotrans.ai.provider"
    _provider_code = "heuristic"

    def infer(self, task, payload, **opts):
        payload = payload or {}
        handler = getattr(self, f"_infer_{task}", None)
        if handler is None:
            raise UserError(f"Unknown AI task: {task!r}")
        return handler(payload, **opts)

    # --- ETA ---------------------------------------------------------------
    def _infer_eta(self, payload, **opts):
        distance = payload.get("distance_km") or haversine_km(
            payload.get("origin_lat"), payload.get("origin_lng"),
            payload.get("dest_lat"), payload.get("dest_lng"),
        )
        service = payload.get("service_level", "standard")
        speed = _SERVICE_SPEED_KMH.get(service, 55.0)
        stops = payload.get("stop_count", 2)
        service_time_h = (stops * 15) / 60.0  # 15 min handling per stop
        congestion = 1.0 + min(0.4, distance / 2000.0)  # longer hauls absorb more delay
        eta_hours = round((distance / speed) * congestion + service_time_h, 2) if distance else 0.0
        confidence = 0.9 if distance else 0.4
        return {"eta_hours": eta_hours, "distance_km": round(distance, 1), "confidence": confidence}

    # --- Delay risk --------------------------------------------------------
    def _infer_risk(self, payload, **opts):
        score = 0.0
        factors = []
        if payload.get("is_late"):
            score += 40
            factors.append("Past SLA due date")
        priority = str(payload.get("priority", "0"))
        if priority == "2":
            score += 15
            factors.append("Urgent priority")
        elif priority == "1":
            score += 8
            factors.append("High priority")
        distance = payload.get("distance_km", 0) or 0
        if distance > 500:
            score += 15
            factors.append("Long-haul distance")
        if payload.get("service_level") in ("express", "same_day"):
            score += 10
            factors.append("Tight service window")
        if payload.get("weather_alert"):
            score += 20
            factors.append("Adverse weather on route")
        if payload.get("temperature_controlled"):
            score += 6
            factors.append("Temperature-sensitive cargo")
        score = max(0.0, min(100.0, score))
        level = "low" if score < 34 else ("medium" if score < 67 else "high")
        return {"score": round(score, 1), "level": level, "factors": factors}

    # --- Dynamic pricing ---------------------------------------------------
    def _infer_price(self, payload, **opts):
        service = payload.get("service_level", "standard")
        base = {"economy": 800, "standard": 1500, "express": 2600, "same_day": 3500}.get(service, 1500)
        distance = payload.get("distance_km", 0) or 0
        weight = payload.get("weight_kg", 0) or 0
        per_km = {"economy": 28, "standard": 35, "express": 55, "same_day": 70}.get(service, 35)
        amount = base + per_km * distance + 2.0 * weight
        demand = float(payload.get("demand_index", 1.0) or 1.0)
        surge = max(1.0, min(2.0, demand))
        amount = round(amount * surge, 2)
        return {
            "amount": amount,
            "surge_multiplier": round(surge, 2),
            "breakdown": {"base": base, "per_km": per_km, "distance_km": round(distance, 1)},
        }

    # --- Anomaly detection -------------------------------------------------
    def _infer_anomaly(self, payload, **opts):
        anomalies = []
        if (payload.get("idle_minutes", 0) or 0) > 90:
            anomalies.append("Excessive idle time")
        if (payload.get("fuel_drop_pct", 0) or 0) > 15:
            anomalies.append("Unexpected fuel drop (possible theft)")
        if (payload.get("route_deviation_km", 0) or 0) > 25:
            anomalies.append("Significant route deviation")
        if payload.get("temp_breach"):
            anomalies.append("Cold-chain temperature breach")
        score = min(100.0, len(anomalies) * 30.0)
        return {"anomalies": anomalies, "score": score}

    # --- Natural-language assistant (rule-based fallback) ------------------
    def _infer_assistant(self, payload, **opts):
        prompt = (payload.get("prompt") or "").lower()
        if not prompt:
            return {"answer": "Ask me about shipments, delays, drivers or routes.", "actions": []}
        if "late" in prompt or "delay" in prompt:
            late = self.env["odotrans.shipment"].search_count([("is_late", "=", True)])
            return {
                "answer": f"There are {late} shipment(s) currently past their SLA. "
                          f"Open the Shipments list filtered on 'Late' to act on them.",
                "actions": [{"type": "filter", "model": "odotrans.shipment", "filter": "is_late"}],
            }
        if "risk" in prompt or "exception" in prompt:
            return {
                "answer": "Run AI Analyze on a shipment to score its delay risk. "
                          "High-risk shipments are flagged in red on the list view.",
                "actions": [],
            }
        if "price" in prompt or "quote" in prompt or "rate" in prompt:
            return {
                "answer": "Use AI Analyze to get a dynamic price suggestion that accounts "
                          "for distance, weight, service level and current demand.",
                "actions": [],
            }
        return {
            "answer": "I can help with delays, risk scoring, pricing and dispatch. "
                      "Try: 'show me late shipments' or 'suggest a price'.",
            "actions": [],
        }

    # --- Document intelligence (stub for offline mode) ---------------------
    def _infer_document(self, payload, **opts):
        return {
            "fields": {},
            "confidence": 0.0,
            "note": "Connect an LLM provider (OpenAI/Azure) to enable document parsing.",
        }


class _LlmMixin:
    """Shared chat-completion plumbing for LLM-backed adapters."""

    def _chat(self, system, user, **opts):  # pragma: no cover - network path
        raise NotImplementedError

    def _llm_json(self, system, user, **opts):
        """Call the LLM and parse a JSON object from the reply."""
        raw = self._chat(system, user, **opts)
        try:
            start, end = raw.find("{"), raw.rfind("}")
            return json.loads(raw[start:end + 1]) if start >= 0 else {}
        except (ValueError, TypeError):
            return {}


class OdotransAiProviderOpenAI(models.AbstractModel):
    """OpenAI adapter. Numeric tasks reuse the heuristic engine (cheap,
    deterministic); language tasks (assistant, document) use the LLM."""

    _name = "odotrans.ai.provider.openai"
    _description = "ODOTRANS AI Provider (OpenAI)"
    _inherit = "odotrans.ai.provider.heuristic"
    _provider_code = "openai"

    def _chat(self, system, user, **opts):  # pragma: no cover - network path
        api_key = self._config("api_key")
        if not api_key:
            raise UserError("OpenAI API key is not configured (Settings > ODOTRANS).")
        model = self._config("model") or "gpt-4o-mini"
        data = self._request(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
        )
        return data["choices"][0]["message"]["content"]

    def _infer_assistant(self, payload, **opts):  # pragma: no cover - network path
        prompt = payload.get("prompt") or ""
        if not self._config("api_key"):
            return super()._infer_assistant(payload, **opts)
        system = (
            "You are ODOTRANS, an expert logistics dispatch assistant. Answer "
            "concisely and operationally. Reply as JSON: {\"answer\": str, \"actions\": []}."
        )
        result = self._llm_json(system, prompt)
        return result or super()._infer_assistant(payload, **opts)


class OdotransAiProviderAzure(models.AbstractModel):
    """Azure OpenAI adapter."""

    _name = "odotrans.ai.provider.azure"
    _description = "ODOTRANS AI Provider (Azure OpenAI)"
    _inherit = "odotrans.ai.provider.openai"
    _provider_code = "azure_openai"

    def _chat(self, system, user, **opts):  # pragma: no cover - network path
        endpoint = self._config("endpoint")
        api_key = self._config("api_key")
        deployment = self._config("deployment")
        if not (endpoint and api_key and deployment):
            raise UserError("Azure OpenAI is not fully configured (Settings > ODOTRANS).")
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-15-preview"
        data = self._request(
            "POST", url,
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
            },
        )
        return data["choices"][0]["message"]["content"]


class OdotransAi(models.AbstractModel):
    """Façade used by all domain code. Delegates to the active adapter."""

    _name = "odotrans.ai"
    _description = "ODOTRANS AI Façade"

    @api.model
    def _provider_registry(self):
        return dict(AI_PROVIDER_REGISTRY)

    @api.model
    def _active_adapter(self):
        code = self.env["ir.config_parameter"].sudo().get_param(
            "odotrans.ai.provider", "heuristic"
        )
        model_name = self._provider_registry().get(code)
        if not model_name or model_name not in self.env:
            # Never hard-fail AI: fall back to the always-available heuristic.
            _logger.warning("AI provider %r unavailable, falling back to heuristic", code)
            model_name = "odotrans.ai.provider.heuristic"
        return self.env[model_name]

    @api.model
    def infer(self, task, payload, **opts):
        return self._active_adapter().infer(task, payload, **opts)

    # Convenience helpers -------------------------------------------------
    @api.model
    def predict_eta(self, payload):
        return self.infer("eta", payload)

    @api.model
    def score_risk(self, payload):
        return self.infer("risk", payload)

    @api.model
    def suggest_price(self, payload):
        return self.infer("price", payload)

    @api.model
    def detect_anomaly(self, payload):
        return self.infer("anomaly", payload)

    @api.model
    def assist(self, prompt, context=None):
        payload = {"prompt": prompt, "context": context or {}}
        return self.infer("assistant", payload)

    @api.model
    def now_iso(self):
        return datetime.utcnow().isoformat()
