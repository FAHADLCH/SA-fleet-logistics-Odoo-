# -*- coding: utf-8 -*-
"""EDI document tracking.

Models the common transportation X12 transaction sets exchanged with
shippers and carriers. Generation here produces a readable, deterministic
representation suitable for demos and as a foundation for a real X12 mapper.
"""
from odoo import api, fields, models


class OdotransEdiDocument(models.Model):
    _name = "odotrans.edi.document"
    _description = "ODOTRANS EDI Document"
    _order = "create_date desc"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Reference", default="New", copy=False, readonly=True)
    edi_type = fields.Selection(
        [
            ("204", "204 — Load Tender"),
            ("214", "214 — Shipment Status"),
            ("210", "210 — Freight Invoice"),
            ("990", "990 — Response to Tender"),
        ],
        string="Transaction Set", required=True, default="204", tracking=True,
    )
    direction = fields.Selection(
        [("in", "Inbound"), ("out", "Outbound")],
        required=True, default="out", tracking=True,
    )
    shipment_id = fields.Many2one("odotrans.shipment", string="Shipment", tracking=True)
    partner_id = fields.Many2one("res.partner", string="Trading Partner")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("generated", "Generated"),
            ("sent", "Sent"),
            ("received", "Received"),
            ("acknowledged", "Acknowledged"),
            ("error", "Error"),
        ],
        default="draft", required=True, tracking=True,
    )
    payload = fields.Text(string="EDI Payload")
    control_number = fields.Char(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "odotrans.edi.document"
                ) or "New"
        return super().create(vals_list)

    def action_generate(self):
        """Produce a deterministic X12-style envelope for the document."""
        for doc in self:
            control = fields.Datetime.now().strftime("%y%m%d%H%M%S")
            doc.control_number = control
            doc.payload = doc._build_payload(control)
            doc.state = "generated"
        return True

    def action_mark_sent(self):
        self.write({"state": "sent"})

    def action_acknowledge(self):
        self.write({"state": "acknowledged"})

    def _build_payload(self, control):
        self.ensure_one()
        ship = self.shipment_id
        segments = [
            "ISA*00*          *00*          *ZZ*ODOTRANS       *ZZ*PARTNER        *%s*U*00401*%s*0*P*>"
            % (fields.Date.today().strftime("%y%m%d"), control),
            "GS*%s*ODOTRANS*PARTNER*%s*%s*1*X*004010"
            % (self._functional_group(), fields.Date.today().strftime("%Y%m%d"), control),
            "ST*%s*0001" % self.edi_type,
        ]
        if ship:
            segments.append("B2**ODOT**%s**PP" % (ship.name or ""))
            if self.edi_type == "214" and ship.state:
                segments.append("AT7*%s***%s" % (self._status_code(ship.state), control))
            if ship.dest_partner_id:
                segments.append("N1*ST*%s" % (ship.dest_partner_id.name or ""))
        segments.append("SE*%s*0001" % (len(segments) + 1))
        segments.append("GE*1*1")
        segments.append("IEA*1*%s" % control)
        return "\n".join(segments)

    def _functional_group(self):
        return {"204": "SM", "214": "QM", "210": "IM", "990": "GF"}.get(self.edi_type, "SM")

    def _status_code(self, state):
        return {
            "in_transit": "AF",
            "delivered": "D1",
            "exception": "SD",
            "planned": "AG",
        }.get(state, "X1")
