# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Base",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Foundation layer for the ODOTRANS logistics operating system",
    "description": """
ODOTRANS Base
=============

Shared foundation for every ODOTRANS bounded context:

* Domain event bus (asynchronous, ``queue_job`` backed) for cross-context
  integration without direct table coupling.
* Reusable mixins: finite state machine and async-dispatch helpers.
* Map / routing provider abstraction with swappable adapters
  (OSRM self-hosted baseline, Google, Mapbox).
* Dedicated queue channels and base security groups.

This module owns no business aggregates. It only provides infrastructure
that the domain addons (``odotrans_tms``, ``odotrans_dispatch`` ...) build on.
""",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "queue_job",
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        "security/odotrans_security.xml",
        "security/ir.model.access.csv",
        "data/queue_job_channel_data.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
