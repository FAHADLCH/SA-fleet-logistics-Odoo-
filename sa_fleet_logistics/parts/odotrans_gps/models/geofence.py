# -*- coding: utf-8 -*-
"""Geofences and crossing events.

A geofence is a circular zone (depot, customer site, restricted area). When a
vehicle's latest snapshot enters/exits a fence we record a crossing and emit a
domain event (e.g. ``geofence.entered``) that ETA recompute or alerts subscribe
to. Evaluation runs on the GPS channel, never in the ingest hot path.
"""
import math

from odoo import api, fields, models

EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


class OdotransGeofence(models.Model):
    _name = "odotrans.geofence"
    _description = "ODOTRANS Geofence"
    _order = "name"

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True,
    )
    center_lat = fields.Float(digits=(10, 7), required=True)
    center_lng = fields.Float(digits=(10, 7), required=True)
    radius_m = fields.Float(string="Radius (m)", required=True, default=200.0)
    kind = fields.Selection(
        [("depot", "Depot"), ("customer", "Customer"), ("restricted", "Restricted")],
        default="customer",
    )

    @api.model
    def evaluate_snapshot(self, vehicle_ids):
        """Check the latest snapshot of each vehicle against active fences."""
        if not vehicle_ids:
            return
        vehicles = self.env["fleet.vehicle"].browse(vehicle_ids).exists()
        fences = self.search([("active", "=", True)])
        if not fences:
            return
        Crossing = self.env["odotrans.geofence.crossing"]
        Bus = self.env["odotrans.event.bus"]
        for v in vehicles:
            if not (v.last_lat and v.last_lng):
                continue
            for fence in fences:
                dist = haversine_m(v.last_lat, v.last_lng, fence.center_lat, fence.center_lng)
                inside = dist <= fence.radius_m
                last = Crossing.search(
                    [("vehicle_id", "=", v.id), ("geofence_id", "=", fence.id)],
                    order="ts desc", limit=1,
                )
                was_inside = bool(last and last.direction == "enter")
                if inside and not was_inside:
                    Crossing.create({
                        "vehicle_id": v.id, "geofence_id": fence.id,
                        "direction": "enter", "ts": v.last_position_ts or fields.Datetime.now(),
                    })
                    Bus.emit("geofence.entered",
                             {"vehicle_id": v.id, "geofence_id": fence.id,
                              "trip_ref": v.active_trip_ref},
                             source_model=self._name, source_res_id=fence.id)
                elif not inside and was_inside:
                    Crossing.create({
                        "vehicle_id": v.id, "geofence_id": fence.id,
                        "direction": "exit", "ts": v.last_position_ts or fields.Datetime.now(),
                    })
                    Bus.emit("geofence.exited",
                             {"vehicle_id": v.id, "geofence_id": fence.id,
                              "trip_ref": v.active_trip_ref},
                             source_model=self._name, source_res_id=fence.id)
        return True


class OdotransGeofenceCrossing(models.Model):
    _name = "odotrans.geofence.crossing"
    _description = "ODOTRANS Geofence Crossing"
    _order = "ts desc"
    _log_access = False

    vehicle_id = fields.Many2one("fleet.vehicle", required=True, ondelete="cascade", index=True)
    geofence_id = fields.Many2one("odotrans.geofence", required=True, ondelete="cascade", index=True)
    direction = fields.Selection([("enter", "Enter"), ("exit", "Exit")], required=True)
    ts = fields.Datetime(required=True, index=True)
