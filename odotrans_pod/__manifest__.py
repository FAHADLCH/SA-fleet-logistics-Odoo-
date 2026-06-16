# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Delivery Proof",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Signatures, photos, OTP and delivery exceptions",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms", "odotrans_dispatch"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/pod_views.xml",
        "views/exception_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
