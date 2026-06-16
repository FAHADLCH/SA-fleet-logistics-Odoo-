# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Regions & Localization",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Region-based configuration for global rollout: units, currency, "
               "compliance (HOS/ELD/tachograph), tax regime and provider overrides",
    "description": """
ODOTRANS Regions & Localization
===============================

Configure ODOTRANS for a worldwide rollout. A *region profile* bundles every
market-specific choice in one place:

* Measurement system (metric / imperial), distance and temperature units.
* Default currency, language and timezone.
* Hours-of-Service / ELD compliance profiles (US FMCSA, EU Tachograph, GCC,
  India AIS-140) with driving-time limits.
* Tax regime (US Sales Tax, EU VAT, GCC VAT, India GST).
* Per-region map and AI provider overrides.
* Sustainability CO₂ factors and feature flags (customs, hazmat, cold chain).

Ships with ready-to-use demo regions for North America, Europe, the GCC and
South Asia.

(c) SA Systems - https://www.sasystems.solutions
""",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_base", "odotrans_tms"],
    "data": [
        "security/odotrans_region_security.xml",
        "security/ir.model.access.csv",
        "views/region_views.xml",
        "views/res_config_settings_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
