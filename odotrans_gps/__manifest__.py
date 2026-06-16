# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS GPS & Telematics",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Position ingest, geofencing and telematics events",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_fleet", "odotrans_dispatch"],
    "data": [
        "security/ir.model.access.csv",
        "views/position_views.xml",
        "views/geofence_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
