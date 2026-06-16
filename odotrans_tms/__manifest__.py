# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS TMS — Logistics Operating System",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Enterprise Transportation Management: shipments, dispatch, "
               "routing, POD, billing & settlement — built for scale",
    "description": """
ODOTRANS — Logistics Operating System
=====================================

The flagship Transportation Management application of the ODOTRANS suite by
SA Systems. ODOTRANS turns Odoo into a real-time, event-driven logistics
operating system designed for 3PLs, fleet operators and high-volume shippers.

This module owns the shipment lifecycle (orders, legs, stops) and acts as the
entry point for the full ODOTRANS platform: Fleet, Dispatch, Route
Optimization, GPS/Telematics, Delivery Proof, Warehouse, Billing, Settlement
and Maintenance.

Engineered for throughput targets of 50,000+ shipments/day using an
asynchronous domain-event bus, queue-worker offloading and a swappable map
provider abstraction (OSRM / Google / Mapbox).

(c) SA Systems - https://www.sasystems.solutions
""",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_base"],
    "data": [
        "security/odotrans_tms_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/shipment_views.xml",
        "views/stop_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
    "auto_install": False,
}
