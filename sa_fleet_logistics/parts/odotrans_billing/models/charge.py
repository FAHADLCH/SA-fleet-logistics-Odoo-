# -*- coding: utf-8 -*-
"""Charges and the rating/invoicing engine.

A ``odotrans.charge`` is a single priced line attached to a shipment. The engine
rates a shipment (on delivery, or on demand) into charges, then invoices them by
creating a standard Odoo ``account.move`` (customer invoice) — so AR, taxes and
reporting all live in core Accounting rather than a parallel ledger.

Invoicing is event-driven: the billing context subscribes to ``pod.delivered``
and enqueues rating on the billing channel, keeping it off the request path.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OdotransCharge(models.Model):
    _name = "odotrans.charge"
    _description = "ODOTRANS Charge"
    _inherit = ["odotrans.async.mixin"]
    _order = "shipment_id, id"

    _odotrans_channel = "root.odotrans.billing"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    shipment_id = fields.Many2one("odotrans.shipment", required=True, ondelete="cascade", index=True)
    customer_id = fields.Many2one(related="shipment_id.customer_id", store=True, index=True)
    charge_type = fields.Selection(
        [("freight", "Freight"), ("fuel", "Fuel Surcharge"),
         ("handling", "Handling"), ("accessorial", "Accessorial")],
        default="freight", required=True,
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id, required=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("invoiced", "Invoiced"), ("cancelled", "Cancelled")],
        default="draft", required=True, index=True,
    )
    move_id = fields.Many2one("account.move", string="Invoice", readonly=True, index=True)
    card_line_id = fields.Many2one("odotrans.rate.card.line", readonly=True)

    # --- rating ------------------------------------------------------------
    @api.model
    def rate_shipment(self, shipment, distance_km=0.0):
        """Create draft charges for a shipment from its matching rate card."""
        if shipment.mapped("charge_ids").filtered(lambda c: c.state != "cancelled"):
            return shipment.charge_ids  # already rated; idempotent
        card = self.env["odotrans.rate.card"].find_for(shipment)
        if not card:
            return self.browse()
        vals_list = []
        for c in card.rate(shipment, distance_km=distance_km):
            vals_list.append({
                "shipment_id": shipment.id,
                "name": c["name"],
                "charge_type": c["charge_type"],
                "amount": c["amount"],
                "card_line_id": c["card_line_id"],
            })
        return self.create(vals_list)

    # --- invoicing ---------------------------------------------------------
    def action_create_invoice(self):
        """Group draft charges by customer into one invoice each."""
        draft = self.filtered(lambda c: c.state == "draft" and c.amount)
        if not draft:
            raise UserError("No draft charges to invoice.")
        moves = self.env["account.move"]
        for customer, charges in self._group_by_customer(draft).items():
            move = self.env["account.move"].create({
                "move_type": "out_invoice",
                "partner_id": customer.id,
                "invoice_origin": ", ".join(charges.mapped("shipment_id.name")),
                "invoice_line_ids": [
                    (0, 0, {
                        "name": f"{ch.shipment_id.name} — {ch.name}",
                        "quantity": 1,
                        "price_unit": ch.amount,
                    }) for ch in charges
                ],
            })
            charges.write({"state": "invoiced", "move_id": move.id})
            moves |= move
        return moves

    def _group_by_customer(self, charges):
        grouped = {}
        for ch in charges:
            grouped.setdefault(ch.customer_id, self.browse())
            grouped[ch.customer_id] |= ch
        return grouped

    # --- event handler -----------------------------------------------------
    @api.model
    def _odotrans_on_shipment_delivered(self, event):
        """Rate + invoice a shipment once it is delivered.

        Runs on the billing channel via queue_job (the event delivery itself is
        already async), so a large delivery burst does not stall other work.
        """
        shipment_id = (event.payload or {}).get("id") or (event.payload or {}).get("shipment_id")
        if not shipment_id:
            return
        shipment = self.env["odotrans.shipment"].browse(shipment_id).exists()
        if not shipment:
            return
        distance_km = self._estimate_distance_km(shipment)
        charges = self.rate_shipment(shipment, distance_km=distance_km)
        if charges:
            charges.action_create_invoice()

    def _estimate_distance_km(self, shipment):
        """Best-effort distance for per-km pricing from the optimization run."""
        run = self.env["odotrans.optimization.run"].search(
            [("trip_id.route_plan_ref", "!=", False)], limit=1,
        ) if "odotrans.optimization.run" in self.env else None
        if run and run.distance_m:
            return run.distance_m / 1000.0
        return 0.0
