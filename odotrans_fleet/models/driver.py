# -*- coding: utf-8 -*-
"""Driver — operational profile linked to an Odoo user and HR employee.

The driver record is the identity the mobile app authenticates as and the
entity settlement pays. Linking to ``res.users`` lets API scopes and record
rules restrict a driver to their own trips/manifests/POD.
"""
from odoo import api, fields, models


class OdotransDriver(models.Model):
    _name = "odotrans.driver"
    _description = "ODOTRANS Driver"
    _inherit = ["mail.thread"]
    _order = "name"

    name = fields.Char(required=True, tracking=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True,
    )
    user_id = fields.Many2one(
        "res.users", string="Login User", index=True,
        help="App login. Record rules scope drivers to their own data via this user.",
    )
    employee_id = fields.Many2one("hr.employee", string="Employee")
    partner_id = fields.Many2one("res.partner", string="Payee", help="Used by settlement.")

    phone = fields.Char()
    license_number = fields.Char(string="License No.", tracking=True)
    license_expiry = fields.Date(tracking=True)
    license_valid = fields.Boolean(compute="_compute_license_valid", store=True)

    status = fields.Selection(
        [
            ("available", "Available"),
            ("on_trip", "On Trip"),
            ("off_duty", "Off Duty"),
        ],
        default="available", tracking=True, index=True,
    )
    default_vehicle_id = fields.Many2one(
        "fleet.vehicle", string="Default Vehicle",
        domain="[('odotrans_enabled','=',True)]",
    )
    active_trip_ref = fields.Char(string="Active Trip", readonly=True, copy=False)

    @api.depends("license_expiry")
    def _compute_license_valid(self):
        today = fields.Date.context_today(self)
        for driver in self:
            driver.license_valid = bool(driver.license_expiry and driver.license_expiry >= today)

    @api.model
    def _odotrans_available_domain(self):
        return [("status", "=", "available"), ("license_valid", "=", True)]

    @api.model
    def _driver_for_user(self, user=None):
        user = user or self.env.user
        return self.search([("user_id", "=", user.id)], limit=1)
