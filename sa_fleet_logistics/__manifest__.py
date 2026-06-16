# -*- coding: utf-8 -*-
{
    "name": "SA Fleet & Logistics",
    "summary": "AI-native 3PL, fleet & transport management for any country: "
               "orders, dispatch, route optimization, live GPS tracking, "
               "proof-of-delivery, warehouse, customer billing and carrier "
               "settlement — multi-currency and region-aware out of the box.",
    "description": """
SA Fleet & Logistics
====================

A complete, **country-agnostic** transport, fleet and **3PL logistics**
operating system for Odoo. One install gives you the full chain — from order
capture to cash — with **multi-currency as standard** and **region-aware**
configuration for a worldwide rollout. Runs on **Odoo 18.0 and 19.0** from a
single codebase.

The Operating Core
------------------
* **Orders & Shipments** — multi-leg, multi-stop transport orders with a clean
  state machine (Draft -> Confirmed -> Dispatched -> In Transit -> POD ->
  Billed -> Settled).
* **Fleet & Drivers** — vehicles, trailers, drivers and compliance assets built
  on Odoo core ``fleet``.
* **Dispatch & Trips** — trip planning, manifests and one-click assignment of
  shipments to vehicles and drivers.
* **Route Optimization** — OSRM / heuristic optimization that sequences stops
  and feeds the plan straight to the trip.
* **Live GPS & Geofencing** — high-volume position ingestion with per-vehicle
  latest-snapshot and geofence crossing events.
* **Proof of Delivery** — mobile-friendly PODs with exceptions, signatures and
  photo capture; a JSON driver API for app integration.
* **Warehouse & Cross-Dock** — docks, bays, waves and pick tasks on top of Odoo
  ``stock``.
* **Customer Billing** — rate cards and charges that post directly to Odoo
  ``account`` invoices.
* **Carrier Settlement** — pay rules, accruals, settlement runs and driver/owner
  pay statements.
* **Maintenance** — preventive-maintenance plans, work orders and defect
  escalation that can ground a vehicle automatically.

AI Intelligence
---------------
* **Predictive ETA & delay risk**, **price suggestions** and shipment scoring
  through a pluggable provider layer (heuristic offline by default; OpenAI /
  Azure OpenAI optional). Never hard-fails — it degrades gracefully to the
  built-in heuristic when no API key is configured.
* **AI Assistant** endpoint for natural-language operational queries.

Global, Multi-Currency & Region-Aware
--------------------------------------
* **Multi-currency by design** — every monetary value carries its own currency
  field and defaults to the company currency, so billing and settlement work in
  any currency with standard Odoo exchange rates.
* **Region profiles** bundle market-specific choices in one place: measurement
  system (metric / imperial), distance units, currency, language, timezone,
  compliance regime (HOS / ELD / tachograph), tax regime and provider overrides.
* Ready-made presets ship for several markets and you can add your own — no
  hard-coded country logic.

Advanced Industry Features
--------------------------
* **Hazmat**, **cold-chain** temperature monitoring, **customs** (incoterm /
  HS code / customs value), **CO2** emissions, **reverse logistics**,
  **detention** and **insurance** on every shipment.
* **Public shipment tracking** portal with a tokenized link and QR code.
* **Dock appointment** booking with a calendar view.

Integration Hub
---------------
* A connector registry for **telematics, EDI, e-commerce, payment, accounting,
  customs, maps and visibility** providers.
* **HMAC-signed webhooks** that fan out platform events asynchronously.
* **EDI** document generation (X12 204 / 214 / 210 / 990) and a secured inbound
  API.

Built On
--------
Leverages Odoo core: ``base``, ``mail``, ``fleet``, ``stock``, ``account`` and
the OCA ``queue_job`` for reliable asynchronous processing. No proprietary
external services are required — deploys on Odoo.sh and on-premise (Community
or Enterprise).

Compatibility
-------------
Verified on **Odoo 18.0 and 19.0** (Community). Uses modern Odoo view syntax
(``<list>``, ``<chatter/>``, ``invisible`` domains), which requires Odoo 18.0
as the minimum supported series.
    """,
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://sasystems.solutions/custom-web-app-development",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "category": "Inventory/Delivery",
    # Series-agnostic version so the module installs on Odoo 18 and 19 alike
    # (a "19.0.x" string is rejected by Odoo 18, and vice-versa). Odoo prefixes
    # the running series automatically, so this reports as 2.0 on both.
    "version": "2.0.0",
    "application": True,
    "installable": True,
    "auto_install": False,
    # --- Odoo Apps store (single paid listing) ---
    "price": 20.0,
    "currency": "USD",
    # Self-contained: only Odoo standard modules and the OCA queue_job. The full
    # platform now ships inside this one module (see parts/).
    "depends": [
        "base",
        "mail",
        "queue_job",
        "fleet",
        "stock",
        "account",
        "web",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        # --- base ---
        "parts/odotrans_base/security/odotrans_security.xml",
        "parts/odotrans_base/security/ir.model.access.csv",
        "parts/odotrans_base/data/queue_job_channel_data.xml",
        "parts/odotrans_base/views/res_config_settings_views.xml",
        # --- tms ---
        "parts/odotrans_tms/security/odotrans_tms_security.xml",
        "parts/odotrans_tms/security/ir.model.access.csv",
        "parts/odotrans_tms/data/ir_sequence_data.xml",
        "parts/odotrans_tms/views/shipment_views.xml",
        "parts/odotrans_tms/views/stop_views.xml",
        "parts/odotrans_tms/views/menus.xml",
        # --- region ---
        "parts/odotrans_region/security/odotrans_region_security.xml",
        "parts/odotrans_region/security/ir.model.access.csv",
        "parts/odotrans_region/views/region_views.xml",
        "parts/odotrans_region/views/res_config_settings_views.xml",
        "parts/odotrans_region/views/menus.xml",
        # --- fleet ---
        "parts/odotrans_fleet/security/odotrans_fleet_security.xml",
        "parts/odotrans_fleet/security/ir.model.access.csv",
        "parts/odotrans_fleet/views/vehicle_views.xml",
        "parts/odotrans_fleet/views/driver_views.xml",
        "parts/odotrans_fleet/views/menus.xml",
        # --- ai ---
        "parts/odotrans_ai/security/odotrans_ai_security.xml",
        "parts/odotrans_ai/security/ir.model.access.csv",
        "parts/odotrans_ai/data/queue_job_channel_data.xml",
        "parts/odotrans_ai/data/event_subscription_data.xml",
        "parts/odotrans_ai/views/ai_insight_views.xml",
        "parts/odotrans_ai/views/shipment_views.xml",
        "parts/odotrans_ai/views/res_config_settings_views.xml",
        "parts/odotrans_ai/wizards/ai_assistant_views.xml",
        "parts/odotrans_ai/views/menus.xml",
        # --- integration ---
        "parts/odotrans_integration/security/odotrans_integration_security.xml",
        "parts/odotrans_integration/security/ir.model.access.csv",
        "parts/odotrans_integration/data/queue_job_channel_data.xml",
        "parts/odotrans_integration/data/event_subscription_data.xml",
        "parts/odotrans_integration/views/connector_views.xml",
        "parts/odotrans_integration/views/webhook_views.xml",
        "parts/odotrans_integration/views/edi_views.xml",
        "parts/odotrans_integration/views/menus.xml",
        # --- dispatch ---
        "parts/odotrans_dispatch/security/odotrans_dispatch_security.xml",
        "parts/odotrans_dispatch/security/ir.model.access.csv",
        "parts/odotrans_dispatch/data/ir_sequence_data.xml",
        "parts/odotrans_dispatch/data/event_subscription_data.xml",
        "parts/odotrans_dispatch/views/trip_views.xml",
        "parts/odotrans_dispatch/views/manifest_views.xml",
        "parts/odotrans_dispatch/views/menus.xml",
        "parts/odotrans_dispatch/wizards/assign_wizard_views.xml",
        # --- warehouse ---
        "parts/odotrans_warehouse/security/ir.model.access.csv",
        "parts/odotrans_warehouse/data/ir_sequence_data.xml",
        "parts/odotrans_warehouse/views/dock_views.xml",
        "parts/odotrans_warehouse/views/wave_views.xml",
        "parts/odotrans_warehouse/views/menus.xml",
        # --- maintenance ---
        "parts/odotrans_maintenance/security/odotrans_maintenance_security.xml",
        "parts/odotrans_maintenance/security/ir.model.access.csv",
        "parts/odotrans_maintenance/data/ir_sequence_data.xml",
        "parts/odotrans_maintenance/data/cron_data.xml",
        "parts/odotrans_maintenance/views/pm_plan_views.xml",
        "parts/odotrans_maintenance/views/work_order_views.xml",
        "parts/odotrans_maintenance/views/defect_views.xml",
        "parts/odotrans_maintenance/views/menus.xml",
        # --- pod ---
        "parts/odotrans_pod/security/ir.model.access.csv",
        "parts/odotrans_pod/data/ir_sequence_data.xml",
        "parts/odotrans_pod/views/pod_views.xml",
        "parts/odotrans_pod/views/exception_views.xml",
        "parts/odotrans_pod/views/menus.xml",
        # --- route ---
        "parts/odotrans_route/security/ir.model.access.csv",
        "parts/odotrans_route/data/ir_sequence_data.xml",
        "parts/odotrans_route/data/event_subscription_data.xml",
        "parts/odotrans_route/views/optimization_run_views.xml",
        "parts/odotrans_route/views/menus.xml",
        "parts/odotrans_route/wizards/optimize_wave_views.xml",
        # --- gps ---
        "parts/odotrans_gps/security/ir.model.access.csv",
        "parts/odotrans_gps/views/position_views.xml",
        "parts/odotrans_gps/views/geofence_views.xml",
        "parts/odotrans_gps/views/menus.xml",
        # --- settlement ---
        "parts/odotrans_settlement/security/odotrans_settlement_security.xml",
        "parts/odotrans_settlement/security/ir.model.access.csv",
        "parts/odotrans_settlement/data/ir_sequence_data.xml",
        "parts/odotrans_settlement/data/event_subscription_data.xml",
        "parts/odotrans_settlement/views/pay_rule_views.xml",
        "parts/odotrans_settlement/views/settlement_run_views.xml",
        "parts/odotrans_settlement/views/menus.xml",
        # --- billing ---
        "parts/odotrans_billing/security/odotrans_billing_security.xml",
        "parts/odotrans_billing/security/ir.model.access.csv",
        "parts/odotrans_billing/data/event_subscription_data.xml",
        "parts/odotrans_billing/views/rate_card_views.xml",
        "parts/odotrans_billing/views/charge_views.xml",
        "parts/odotrans_billing/views/menus.xml",
        # --- advanced ---
        "parts/odotrans_advanced/security/odotrans_advanced_security.xml",
        "parts/odotrans_advanced/security/ir.model.access.csv",
        "parts/odotrans_advanced/data/sequence_data.xml",
        "parts/odotrans_advanced/views/appointment_views.xml",
        "parts/odotrans_advanced/views/shipment_views.xml",
        "parts/odotrans_advanced/views/tracking_templates.xml",
        "parts/odotrans_advanced/views/menus.xml",
        # --- driver_api: controllers only, no data ---
    ],
    "demo": [
        "parts/odotrans_tms/demo/demo_data.xml",
        "parts/odotrans_fleet/demo/demo_data.xml",
        "parts/odotrans_region/demo/demo_data.xml",
        "parts/odotrans_gps/demo/demo_data.xml",
        "parts/odotrans_maintenance/demo/demo_data.xml",
        "parts/odotrans_billing/demo/demo_data.xml",
        "parts/odotrans_settlement/demo/demo_data.xml",
        "parts/odotrans_advanced/demo/demo_data.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
}
