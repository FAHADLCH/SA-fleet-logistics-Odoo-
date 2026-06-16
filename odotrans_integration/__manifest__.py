# -*- coding: utf-8 -*-
{
    "name": "ODOTRANS Integration Hub",
    "version": "2.0.0",
    "category": "Inventory/Delivery",
    "summary": "Connector registry, outbound webhooks, inbound API and EDI "
               "(X12 204/214/210/990) for telematics, EDI, e-commerce, payments, "
               "accounting and customs integrations",
    "description": """
ODOTRANS Integration Hub
=======================

A single control panel for everything ODOTRANS talks to:

* **Connector registry** — register telematics (Samsara, Geotab), e-commerce
  (Shopify), payments (Stripe), accounting (QuickBooks) and visibility
  (project44) endpoints with credentials, status and test-connection.
* **Outbound webhooks** — subscribe HTTP endpoints to ODOTRANS events
  (``odotrans_shipment.*``, ``odotrans_trip.*``, ``pod.*``) with HMAC signing.
* **Inbound API** — secured ``/odotrans/api/v1/integration/inbound/<code>``
  endpoint for partner callbacks.
* **EDI documents** — generate and track X12 204 (tender), 214 (status),
  210 (invoice) and 990 (response) messages.

Outbound delivery runs asynchronously on the OCA ``queue_job`` bus so a slow
partner never blocks operations.

(c) SA Systems - https://www.sasystems.solutions
""",
    "author": "SA Systems",
    "maintainer": "SA Systems",
    "website": "https://www.sasystems.solutions",
    "support": "info@sasystems.solutions",
    "license": "LGPL-3",
    "depends": ["odotrans_tms"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/odotrans_integration_security.xml",
        "security/ir.model.access.csv",
        "data/queue_job_channel_data.xml",
        "data/event_subscription_data.xml",
        "views/connector_views.xml",
        "views/webhook_views.xml",
        "views/edi_views.xml",
        "views/menus.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
