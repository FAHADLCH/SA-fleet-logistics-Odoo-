# -*- coding: utf-8 -*-
"""Connector registry.

Each record represents one external system ODOTRANS integrates with. Secrets
are stored per-connector; a manual *Test Connection* probes the endpoint and
records the result so operators can see integration health at a glance.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OdotransIntegrationConnector(models.Model):
    _name = "odotrans.integration.connector"
    _description = "ODOTRANS Integration Connector"
    _order = "category, name"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, help="Unique short code, e.g. samsara, stripe.")
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("telematics", "Telematics / GPS"),
            ("edi", "EDI"),
            ("ecommerce", "E-Commerce"),
            ("payment", "Payment"),
            ("accounting", "Accounting"),
            ("customs", "Customs"),
            ("maps", "Maps & Routing"),
            ("visibility", "Visibility"),
            ("other", "Other"),
        ],
        required=True, default="other", tracking=True,
    )
    provider = fields.Char(help="Vendor / product name.")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True,
    )

    auth_type = fields.Selection(
        [
            ("none", "None"),
            ("api_key", "API Key"),
            ("bearer", "Bearer Token"),
            ("basic", "Basic Auth"),
            ("oauth2", "OAuth 2.0"),
        ],
        default="api_key", required=True,
    )
    base_url = fields.Char(string="Base URL")
    api_key = fields.Char(string="API Key / Token")
    username = fields.Char()
    password = fields.Char()

    status = fields.Selection(
        [
            ("draft", "Not Connected"),
            ("ok", "Connected"),
            ("error", "Error"),
        ],
        default="draft", readonly=True, tracking=True,
    )
    last_sync = fields.Datetime(string="Last Activity", readonly=True)
    last_error = fields.Char(readonly=True)

    _sql_constraints = [
        ("code_company_uniq", "unique(code, company_id)",
         "Connector code must be unique per company."),
    ]

    def _auth_headers(self):
        self.ensure_one()
        headers = {"Content-Type": "application/json"}
        if self.auth_type == "api_key" and self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_type == "bearer" and self.api_key:
            headers["Authorization"] = "Bearer %s" % self.api_key
        return headers

    def action_test_connection(self):
        """Probe ``base_url`` and record the outcome.

        Designed to fail soft: any network/credential error is captured on the
        record rather than raised, so the registry stays usable offline.
        """
        for connector in self:
            if not connector.base_url:
                connector.write({
                    "status": "error",
                    "last_error": "No base URL configured.",
                })
                continue
            try:
                import requests
                auth = None
                if connector.auth_type == "basic":
                    auth = (connector.username or "", connector.password or "")
                response = requests.get(
                    connector.base_url,
                    headers=connector._auth_headers(),
                    auth=auth,
                    timeout=10,
                )
                if response.status_code < 500:
                    connector.write({
                        "status": "ok",
                        "last_sync": fields.Datetime.now(),
                        "last_error": False,
                    })
                else:
                    connector.write({
                        "status": "error",
                        "last_error": "HTTP %s" % response.status_code,
                    })
            except Exception as exc:  # noqa: BLE001 - reported on the record
                _logger.warning("Connector %s test failed: %s", connector.code, exc)
                connector.write({"status": "error", "last_error": str(exc)[:200]})
        return True
