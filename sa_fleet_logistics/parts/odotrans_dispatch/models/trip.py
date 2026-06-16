# -*- coding: utf-8 -*-
"""Trip — the dispatch aggregate: a vehicle+driver executing a set of legs.

The trip is where planning becomes execution. It enforces capacity constraints,
links back to TMS legs via their ``trip_ref`` soft link, and drives the manifest.
Lifecycle transitions emit events that GPS/POD/settlement consume.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class OdotransTrip(models.Model):
    _name = "odotrans.trip"
    _description = "ODOTRANS Trip"
    _inherit = ["odotrans.state.mixin", "odotrans.async.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "scheduled_start desc, id desc"

    _odotrans_state_field = "state"
    _odotrans_transitions = {
        "draft": ["assigned", "cancelled"],
        "assigned": ["dispatched", "draft", "cancelled"],
        "dispatched": ["in_progress", "cancelled"],
        "in_progress": ["completed", "exception"],
        "exception": ["in_progress", "completed", "cancelled"],
        "completed": [],
    }

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("assigned", "Assigned"),
            ("dispatched", "Dispatched"),
            ("in_progress", "In Progress"),
            ("exception", "Exception"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True, index=True,
    )
    vehicle_id = fields.Many2one(
        "fleet.vehicle", string="Vehicle", tracking=True,
        domain="[('odotrans_enabled','=',True)]",
    )
    driver_id = fields.Many2one("odotrans.driver", string="Driver", tracking=True)

    scheduled_start = fields.Datetime(index=True)
    scheduled_end = fields.Datetime()
    actual_start = fields.Datetime(readonly=True)
    actual_end = fields.Datetime(readonly=True)
    start_odometer = fields.Float(readonly=True)
    end_odometer = fields.Float(readonly=True)

    leg_ids = fields.One2many("odotrans.leg", compute="_compute_leg_ids", string="Legs")
    manifest_id = fields.Many2one("odotrans.manifest", readonly=True, copy=False)
    stop_ids = fields.Many2many(related="manifest_id.stop_ids", string="Stops")

    # Plan reference produced by the route-optimization context.
    route_plan_ref = fields.Char(string="Route Plan", readonly=True, copy=False)

    total_weight_kg = fields.Float(compute="_compute_load", store=True)
    total_volume_m3 = fields.Float(compute="_compute_load", store=True)
    stop_count = fields.Integer(compute="_compute_load", store=True)

    @api.depends("name")
    def _compute_leg_ids(self):
        Leg = self.env["odotrans.leg"]
        for trip in self:
            trip.leg_ids = Leg.search([("trip_ref", "=", trip.name)]) if trip.name and trip.name != "New" else Leg

    @api.depends("manifest_id.stop_ids", "manifest_id.stop_ids.shipment_id")
    def _compute_load(self):
        for trip in self:
            shipments = trip.mapped("manifest_id.stop_ids.shipment_id")
            trip.total_weight_kg = sum(shipments.mapped("weight_kg"))
            trip.total_volume_m3 = sum(shipments.mapped("volume_m3"))
            trip.stop_count = len(trip.manifest_id.stop_ids)

    @api.constrains("vehicle_id", "total_weight_kg", "total_volume_m3")
    def _check_capacity(self):
        for trip in self:
            v = trip.vehicle_id
            if not v:
                continue
            if v.capacity_weight_kg and trip.total_weight_kg > v.capacity_weight_kg:
                raise ValidationError(
                    f"Trip {trip.name}: load {trip.total_weight_kg}kg exceeds "
                    f"vehicle capacity {v.capacity_weight_kg}kg."
                )
            if v.capacity_volume_m3 and trip.total_volume_m3 > v.capacity_volume_m3:
                raise ValidationError(
                    f"Trip {trip.name}: volume {trip.total_volume_m3}m³ exceeds "
                    f"vehicle capacity {v.capacity_volume_m3}m³."
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.trip") or "New"
        trips = super().create(vals_list)
        for trip in trips:
            trip.manifest_id = self.env["odotrans.manifest"].create({"trip_id": trip.id}).id
        return trips

    # --- actions -----------------------------------------------------------
    def assign(self, vehicle_id=None, driver_id=None):
        """Assign vehicle + driver, marking both busy and linking legs."""
        for trip in self:
            if vehicle_id:
                trip.vehicle_id = vehicle_id
            if driver_id:
                trip.driver_id = driver_id
            if not (trip.vehicle_id and trip.driver_id):
                raise UserError("A trip needs both a vehicle and a driver to be assigned.")
            trip._check_capacity()
            trip.vehicle_id.write({"odotrans_status": "on_trip", "active_trip_ref": trip.name})
            trip.driver_id.write({"status": "on_trip", "active_trip_ref": trip.name})
            trip._transition_to("assigned")
        return True

    def action_dispatch(self):
        for trip in self:
            if not trip.manifest_id.stop_ids:
                raise UserError(f"Trip {trip.name} has no stops to dispatch.")
            trip._transition_to("dispatched")
            # Notify the driver app asynchronously.
            trip.with_delay(
                channel="root.odotrans.notify",
                description=f"Push manifest {trip.name}",
            )._notify_driver()
        return True

    def action_start(self):
        for trip in self:
            trip.write({"actual_start": fields.Datetime.now()})
            if trip.vehicle_id:
                trip.start_odometer = trip.vehicle_id.odometer
            trip._transition_to("in_progress")

    def action_complete(self):
        for trip in self:
            trip.write({"actual_end": fields.Datetime.now()})
            trip._transition_to("completed")
            trip._release_resources()

    def action_cancel(self):
        for trip in self:
            trip._transition_to("cancelled")
            trip._release_resources()

    def _release_resources(self):
        for trip in self:
            if trip.vehicle_id:
                trip.vehicle_id.write({"odotrans_status": "available", "active_trip_ref": False})
            if trip.driver_id:
                trip.driver_id.write({"status": "available", "active_trip_ref": False})

    def _notify_driver(self):
        """Placeholder for WebSocket/push fan-out (handled by driver_api)."""
        self.env["odotrans.event.bus"].emit(
            topic="trip.dispatched",
            payload={"trip_id": self.id, "trip": self.name,
                     "driver_id": self.driver_id.id, "vehicle_id": self.vehicle_id.id},
            source_model=self._name, source_res_id=self.id,
        )
        return True

    # --- event handlers ----------------------------------------------------
    @api.model
    def _odotrans_on_shipment_confirmed(self, event):
        """When a shipment is confirmed, surface it as a dispatchable activity.

        We do not auto-create trips (planning may consolidate many shipments);
        instead we log so dispatchers/optimization can pick it up. The route
        context listens to the same topic to enqueue optimization.
        """
        return True
