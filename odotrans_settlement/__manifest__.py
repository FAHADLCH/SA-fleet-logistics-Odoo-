# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Settlement",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Driver and carrier pay runs, deductions",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_dispatch", "account"],
    "data": [
        "security/odotrans_settlement_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/event_subscription_data.xml",
        "views/pay_rule_views.xml",
        "views/settlement_run_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
