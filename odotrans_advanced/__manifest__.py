# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Advanced Logistics",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Industry-grade capabilities: dangerous goods, cold chain, "
               "customs & cross-border, sustainability (CO₂), reverse logistics, "
               "detention/demurrage, dock appointments and a public tracking portal",
    "description": """
ODOTRANS Advanced Logistics
==========================

Closes the feature gaps that separate a basic TMS from a global 3PL platform:

* **Dangerous goods** — UN number, hazard class, packing group, placards.
* **Cold chain** — temperature range, reefer requirement and breach tracking.
* **Customs & cross-border** — Incoterms, HS code, customs value and status.
* **Sustainability** — CO₂e computed from the shipment's region emission factor.
* **Reverse logistics** — returns linked back to the original shipment.
* **Detention & demurrage** — automatic minute/charge accrual.
* **Cargo insurance** — declared insured value.
* **Dock appointments** — book a dock + time window per shipment.
* **Public tracking portal** — branded ``/odotrans/track`` page for customers.

(c) SA Systems - https://www.sasystems.solutions
""",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms", "odotrans_region", "web"],
    "data": [
        "security/odotrans_advanced_security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/appointment_views.xml",
        "views/shipment_views.xml",
        "views/tracking_templates.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
