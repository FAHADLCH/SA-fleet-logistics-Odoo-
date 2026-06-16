# -*- coding: utf-8 -*-
"""Manifest — the ordered, printable execution document for a trip.

The manifest holds the sequenced stops the driver must visit. Sequencing is
written by the route-optimization context (or manually by a dispatcher). Stops
themselves remain owned by TMS; the manifest references them and adds the
trip-level ordering + per-stop dispatch status rollup.
"""
from odoo import api, fields, models


class OdotransManifest(models.Model):
    _name = "odotrans.manifest"
    _description = "ODOTRANS Manifest"
    _order = "id desc"

    name = fields.Char(compute="_compute_name", store=True)
    trip_id = fields.Many2one("odotrans.trip", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="trip_id.company_id", store=True, index=True)
    line_ids = fields.One2many("odotrans.manifest.line", "manifest_id", string="Lines")
    stop_ids = fields.Many2many(
        "odotrans.stop", compute="_compute_stop_ids", string="Stops",
    )
    line_count = fields.Integer(compute="_compute_stop_ids")

    @api.depends("trip_id.name")
    def _compute_name(self):
        for m in self:
            m.name = f"MAN/{m.trip_id.name}" if m.trip_id else "MAN/New"

    @api.depends("line_ids.stop_id")
    def _compute_stop_ids(self):
        for m in self:
            m.stop_ids = m.line_ids.mapped("stop_id")
            m.line_count = len(m.line_ids)

    def add_stops(self, stops, start_seq=10, step=10):
        """Append stops (recordset) to the manifest in order."""
        self.ensure_one()
        Line = self.env["odotrans.manifest.line"]
        seq = start_seq
        created = Line
        for stop in stops:
            created |= Line.create({"manifest_id": self.id, "stop_id": stop.id, "sequence": seq})
            seq += step
        return created

    def apply_sequence(self, ordered_stop_ids):
        """Re-order lines to match an optimizer-provided stop id ordering."""
        self.ensure_one()
        seq = 10
        for stop_id in ordered_stop_ids:
            line = self.line_ids.filtered(lambda l: l.stop_id.id == stop_id)
            if line:
                line.sequence = seq
                seq += 10
        return True


class OdotransManifestLine(models.Model):
    _name = "odotrans.manifest.line"
    _description = "ODOTRANS Manifest Line"
    _order = "manifest_id, sequence, id"

    manifest_id = fields.Many2one(
        "odotrans.manifest", required=True, ondelete="cascade", index=True,
    )
    sequence = fields.Integer(default=10)
    stop_id = fields.Many2one("odotrans.stop", required=True, ondelete="cascade", index=True)
    shipment_id = fields.Many2one(related="stop_id.shipment_id", store=True)
    stop_type = fields.Selection(related="stop_id.stop_type", store=True)
    stop_state = fields.Selection(related="stop_id.state")
    planned_eta = fields.Datetime(related="stop_id.planned_eta", readonly=False)
