# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Warehouse",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Docks, waves, cross-dock and freight handling",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms", "stock"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/dock_views.xml",
        "views/wave_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
