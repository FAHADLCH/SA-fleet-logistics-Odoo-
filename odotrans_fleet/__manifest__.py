# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Fleet",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Vehicles, drivers, trailers and compliance assets",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_base", "odotrans_tms", "fleet"],
    "data": [
        "security/odotrans_fleet_security.xml",
        "security/ir.model.access.csv",
        "views/vehicle_views.xml",
        "views/driver_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
