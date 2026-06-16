# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Maintenance",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Preventive maintenance plans, work orders and defects",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_fleet"],
    "data": [
        "security/odotrans_maintenance_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/cron_data.xml",
        "views/pm_plan_views.xml",
        "views/work_order_views.xml",
        "views/defect_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
