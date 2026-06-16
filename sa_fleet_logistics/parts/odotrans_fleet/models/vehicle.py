# -*- coding: utf-8 -*-
"""Vehicle — extends Odoo ``fleet.vehicle`` with logistics operating attributes.

We deliberately extend the standard fleet model rather than reinventing it, so
ODOTRANS inherits Odoo's odometer, contracts and cost tracking for free, and
adds only what dispatch/optimization need: capacity, operational status and a
live position snapshot (kept tiny — the full trace lives in the GPS context).
"""
from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    odotrans_enabled = fields.Boolean(string="ODOTRANS Asset", default=True, index=True)
    odotrans_status = fields.Selection(
        [
            ("available", "Available"),
            ("on_trip", "On Trip"),
            ("maintenance", "Maintenance"),
            ("out_of_service", "Out of Service"),
        ],
        default="available", tracking=True, index=True,
    )
    capacity_weight_kg = fields.Float(string="Capacity (kg)")
    capacity_volume_m3 = fields.Float(string="Capacity (m³)")
    capacity_pallets = fields.Integer(string="Capacity (pallets)")

    # Lightweight live snapshot; high-frequency history is in odotrans.position.
    last_lat = fields.Float(digits=(10, 7), readonly=True)
    last_lng = fields.Float(digits=(10, 7), readonly=True)
    last_position_ts = fields.Datetime(readonly=True)

    # Soft link to the active trip (owned by dispatch context).
    active_trip_ref = fields.Char(string="Active Trip", readonly=True, copy=False)

    def action_set_available(self):
        self.write({"odotrans_status": "available", "active_trip_ref": False})

    def action_set_maintenance(self):
        self.write({"odotrans_status": "maintenance"})

    @api.model
    def _odotrans_available_domain(self):
        return [("odotrans_enabled", "=", True), ("odotrans_status", "=", "available")]

    # --- event handlers ----------------------------------------------------
    @api.model
    def _odotrans_on_vehicle_down(self, event):
        """Maintenance context flags a vehicle down -> remove from pool."""
        vehicle_id = (event.payload or {}).get("vehicle_id")
        if vehicle_id:
            self.browse(vehicle_id).exists().write({"odotrans_status": "maintenance"})
