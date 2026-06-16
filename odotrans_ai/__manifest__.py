# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS AI Intelligence",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Predictive ETA, delay-risk scoring, dynamic pricing, anomaly "
               "detection and a natural-language dispatch assistant",
    "description": """
ODOTRANS AI Intelligence
========================

Adds a provider-abstracted AI layer to the ODOTRANS logistics platform:

* Predictive ETA and transit-time estimation.
* Delay / exception risk scoring with explainable factors.
* Dynamic price suggestions driven by distance, weight and demand.
* Anomaly detection (idle, fuel drop, route deviation, cold-chain breach).
* Natural-language dispatch assistant (backend wizard + JSON API).

Ships with a deterministic, offline ``heuristic`` engine that works with no
API key, and pluggable OpenAI / Azure OpenAI adapters for production-grade
language tasks. Every prediction is persisted as an auditable AI Insight.

(c) SA Systems - https://www.sasystems.solutions
""",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/odotrans_ai_security.xml",
        "security/ir.model.access.csv",
        "data/queue_job_channel_data.xml",
        "data/event_subscription_data.xml",
        "views/ai_insight_views.xml",
        "views/shipment_views.xml",
        "views/res_config_settings_views.xml",
        "wizards/ai_assistant_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
