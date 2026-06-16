# -*- coding: utf-8 -*-
"""Public, token-protected shipment tracking portal.

A customer with a shipment's access token can view live status without an
ODOTRANS account. The token is an unguessable 32-char URL-safe string, so the
endpoint is safe to expose with ``auth="public"``.
"""
from odoo import http
from odoo.http import request


class OdotransTrackingController(http.Controller):

    @http.route(
        ["/odotrans/track", "/odotrans/track/<string:token>"],
        type="http", auth="public", website=False, csrf=False, sitemap=False,
    )
    def track(self, token=None, **kwargs):
        token = token or kwargs.get("token")
        shipment = None
        if token:
            shipment = (
                request.env["odotrans.shipment"]
                .sudo()
                .search([("access_token", "=", token)], limit=1)
            )
        values = {
            "token": token,
            "shipment": shipment,
            "not_found": bool(token) and not shipment,
        }
        return request.render("sa_fleet_logistics.tracking_page", values)
