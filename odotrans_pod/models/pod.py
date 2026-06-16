# -*- coding: utf-8 -*-
"""Proof of Delivery — captured at a stop by the driver app.

A POD records who received the goods and the evidence (signature, photos, OTP).
On confirmation it marks the stop done and, when all drops on the shipment are
complete, emits ``pod.delivered`` — the TMS shipment subscribes to that event
and transitions to *delivered*, which in turn triggers billing + settlement.

Binary evidence is stored as ``ir.attachment`` (which can be offloaded to S3-
compatible object storage), never inline in the transactional row.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OdotransPod(models.Model):
    _name = "odotrans.pod"
    _description = "ODOTRANS Proof of Delivery"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    stop_id = fields.Many2one("odotrans.stop", required=True, ondelete="cascade", index=True)
    shipment_id = fields.Many2one(related="stop_id.shipment_id", store=True, index=True)
    trip_ref = fields.Char(index=True)
    driver_id = fields.Many2one("odotrans.driver", index=True)

    method = fields.Selection(
        [("signature", "Signature"), ("photo", "Photo"), ("otp", "OTP"), ("none", "None")],
        default="signature", required=True,
    )
    received_by = fields.Char(string="Received By")
    captured_at = fields.Datetime(default=fields.Datetime.now)
    lat = fields.Float(digits=(10, 7))
    lng = fields.Float(digits=(10, 7))

    signature = fields.Binary(attachment=True)
    photo_ids = fields.Many2many("ir.attachment", string="Photos")
    otp_code = fields.Char(string="OTP")
    otp_verified = fields.Boolean(default=False)

    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("rejected", "Rejected")],
        default="draft", required=True, tracking=True, index=True,
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.pod") or "New"
        return super().create(vals_list)

    def action_confirm(self):
        for pod in self:
            pod._validate_evidence()
            pod.state = "confirmed"
            if pod.stop_id.state != "done":
                pod.stop_id.action_mark_done()
            pod._maybe_emit_delivered()
        return True

    def _validate_evidence(self):
        for pod in self:
            if pod.method == "signature" and not pod.signature:
                raise UserError("Signature POD requires a captured signature.")
            if pod.method == "photo" and not pod.photo_ids:
                raise UserError("Photo POD requires at least one photo.")
            if pod.method == "otp" and not pod.otp_verified:
                raise UserError("OTP POD requires a verified code.")

    def _maybe_emit_delivered(self):
        """Emit pod.delivered once every drop stop of the shipment is done."""
        for pod in self:
            shipment = pod.shipment_id
            if not shipment:
                continue
            drops = shipment.mapped("leg_ids.stop_ids").filtered(lambda s: s.stop_type == "drop")
            if drops and all(s.state == "done" for s in drops):
                self.env["odotrans.event.bus"].emit(
                    topic="pod.delivered",
                    payload={"shipment_id": shipment.id, "ref": shipment.name,
                             "pod_id": pod.id, "trip_ref": pod.trip_ref},
                    source_model=self._name, source_res_id=pod.id,
                )

    def verify_otp(self, code):
        self.ensure_one()
        if code and self.otp_code and code == self.otp_code:
            self.otp_verified = True
            return True
        return False
