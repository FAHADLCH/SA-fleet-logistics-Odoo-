# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Billing",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Rate cards, rating engine and customer invoicing",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms", "odotrans_route", "account"],
    "data": [
        "security/odotrans_billing_security.xml",
        "security/ir.model.access.csv",
        "data/event_subscription_data.xml",
        "views/rate_card_views.xml",
        "views/charge_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
