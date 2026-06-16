# -*- coding: utf-8 -*-
"""Dock appointment scheduling for inbound/outbound shipments."""
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class OdotransAppointment(models.Model):
    _name = "odotrans.appointment"
    _description = "ODOTRANS Dock Appointment"
    _order = "start_datetime desc"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Reference", default="New", copy=False, readonly=True)
    shipment_id = fields.Many2one(
        "odotrans.shipment", string="Shipment", required=True,
        ondelete="cascade", tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", related="shipment_id.company_id", store=True, readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Facility", help="Warehouse or facility partner.",
    )
    dock = fields.Char(string="Dock / Door")
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")],
        default="inbound", required=True, tracking=True,
    )
    start_datetime = fields.Datetime(string="Window Start", required=True, tracking=True)
    end_datetime = fields.Datetime(string="Window End", required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Requested"),
            ("confirmed", "Confirmed"),
            ("arrived", "Arrived"),
            ("done", "Completed"),
            ("no_show", "No-Show"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True,
    )
    notes = fields.Text(string="Notes")

    @api.constrains("start_datetime", "end_datetime")
    def _check_window(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime and rec.end_datetime <= rec.start_datetime:
                raise ValidationError("Window end must be after window start.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "odotrans.appointment"
                ) or "New"
        return super().create(vals_list)

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_arrived(self):
        self.write({"state": "arrived"})

    def action_done(self):
        self.write({"state": "done"})

    def action_no_show(self):
        self.write({"state": "no_show"})

    def action_cancel(self):
        self.write({"state": "cancelled"})
