# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Route Optimization",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "VRP optimization runs backed by the map provider abstraction",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms", "odotrans_dispatch"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/event_subscription_data.xml",
        "views/optimization_run_views.xml",
        "views/menus.xml",
        "wizards/optimize_wave_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
