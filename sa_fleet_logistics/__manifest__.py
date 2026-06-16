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
    # --- Odoo Apps store (paid listing) ---
    "price": 5.0,
    "currency": "USD",
    "depends": [
        # Installing the umbrella pulls in the entire SA Fleet & Logistics
        # platform. These leaf modules transitively install base, tms, fleet,
        # dispatch and the rest.
        "odotrans_billing",
        "odotrans_settlement",
        "odotrans_maintenance",
        "odotrans_warehouse",
        "odotrans_route",
        "odotrans_gps",
        "odotrans_pod",
        "odotrans_driver_api",
        "odotrans_ai",
        "odotrans_region",
        "odotrans_advanced",
        "odotrans_integration",
    ],
    "data": [],
    "images": [
        "static/description/banner.png",
    ],
}
