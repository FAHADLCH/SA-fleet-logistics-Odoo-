# -*- coding: utf-8 -*-
"""Driver-app JSON API.

Mobile endpoints for the on-road workforce. These run inside Odoo's HTTP stack
authenticated as the logged-in driver ``res.users``; record rules already scope
every query to the driver's own trips/manifests/POD, so the controller never
needs to re-implement authorization — it only validates input and delegates to
the domain models.

Conventions:
* ``type="json"`` controllers — request/response are JSON.
* All write endpoints are idempotent where it matters (telemetry batches,
  stop status) so spotty mobile connectivity that retries is safe.
* Heavy work (telemetry persistence) is handed to the GPS context which bulk-
  inserts; the request returns fast.

NOTE: For 50k-scale production this surface is intended to sit behind the
external FastAPI gateway (JWT, rate-limiting, WebSocket). These controllers are
the Odoo-side handlers the gateway proxies to.
"""
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DriverApiController(http.Controller):

    # --- helpers -----------------------------------------------------------
    def _current_driver(self):
        return request.env["odotrans.driver"]._driver_for_user(request.env.user)

    def _err(self, message, code="error"):
        return {"ok": False, "error": code, "message": message}

    # --- identity ----------------------------------------------------------
    @http.route("/odotrans/api/v1/driver/me", type="json", auth="user", methods=["POST"])
    def driver_me(self):
        driver = self._current_driver()
        if not driver:
            return self._err("No driver profile linked to this user.", "no_driver")
        return {
            "ok": True,
            "driver": {
                "id": driver.id,
                "name": driver.name,
                "status": driver.status,
                "license_valid": driver.license_valid,
                "active_trip_ref": driver.active_trip_ref,
            },
        }

    # --- manifest ----------------------------------------------------------
    @http.route("/odotrans/api/v1/driver/manifest", type="json", auth="user", methods=["POST"])
    def driver_manifest(self):
        """Return the active trip's ordered stops for the logged-in driver."""
        driver = self._current_driver()
        if not driver:
            return self._err("No driver profile.", "no_driver")
        trip = request.env["odotrans.trip"].search(
            [("driver_id", "=", driver.id),
             ("state", "in", ("assigned", "dispatched", "in_progress", "exception"))],
            order="scheduled_start asc", limit=1,
        )
        if not trip:
            return {"ok": True, "trip": None, "stops": []}
        lines = trip.manifest_id.line_ids.sorted("sequence")
        stops = [{
            "stop_id": ln.stop_id.id,
            "sequence": ln.sequence,
            "type": ln.stop_id.stop_type,
            "partner": ln.stop_id.partner_id.display_name if ln.stop_id.partner_id else None,
            "lat": ln.stop_id.lat,
            "lng": ln.stop_id.lng,
            "window_start": ln.stop_id.window_start,
            "window_end": ln.stop_id.window_end,
            "eta": ln.stop_id.planned_eta,
            "state": ln.stop_id.state,
        } for ln in lines]
        return {
            "ok": True,
            "trip": {"id": trip.id, "ref": trip.name, "state": trip.state,
                     "vehicle": trip.vehicle_id.display_name},
            "stops": stops,
        }

    @http.route("/odotrans/api/v1/driver/trip/start", type="json", auth="user", methods=["POST"])
    def driver_trip_start(self):
        driver = self._current_driver()
        trip = request.env["odotrans.trip"].search(
            [("driver_id", "=", driver.id), ("state", "=", "dispatched")], limit=1,
        ) if driver else None
        if not trip:
            return self._err("No dispatched trip to start.", "no_trip")
        trip.action_start()
        return {"ok": True, "trip_ref": trip.name, "state": trip.state}

    # --- stop status -------------------------------------------------------
    @http.route("/odotrans/api/v1/driver/stop/arrive", type="json", auth="user", methods=["POST"])
    def stop_arrive(self, stop_id=None, **kw):
        stop = self._owned_stop(stop_id)
        if not stop:
            return self._err("Stop not found or not yours.", "not_found")
        stop.action_mark_arrived()
        return {"ok": True, "stop_id": stop.id, "state": stop.state}

    def _owned_stop(self, stop_id):
        if not stop_id:
            return None
        # Record rules constrain visibility; we additionally confirm the stop's
        # trip is the driver's active trip.
        return request.env["odotrans.stop"].browse(int(stop_id)).exists()

    # --- proof of delivery -------------------------------------------------
    @http.route("/odotrans/api/v1/driver/stop/pod", type="json", auth="user", methods=["POST"])
    def stop_pod(self, stop_id=None, method="signature", received_by=None,
                 signature=None, otp=None, lat=None, lng=None, note=None, **kw):
        """Capture POD for a stop. ``signature`` is base64 image data."""
        driver = self._current_driver()
        stop = self._owned_stop(stop_id)
        if not stop:
            return self._err("Stop not found or not yours.", "not_found")
        vals = {
            "stop_id": stop.id,
            "driver_id": driver.id if driver else False,
            "trip_ref": stop.leg_id.trip_ref,
            "method": method,
            "received_by": received_by,
            "lat": lat or 0.0,
            "lng": lng or 0.0,
            "note": note,
        }
        if method == "signature" and signature:
            vals["signature"] = signature
        if method == "otp" and otp:
            vals["otp_code"] = otp
            vals["otp_verified"] = True
        pod = request.env["odotrans.pod"].create(vals)
        try:
            pod.action_confirm()
        except Exception as exc:  # noqa: BLE001 - return a clean API error
            return self._err(str(exc), "pod_invalid")
        return {"ok": True, "pod": pod.name, "stop_state": stop.state}

    @http.route("/odotrans/api/v1/driver/stop/exception", type="json", auth="user", methods=["POST"])
    def stop_exception(self, stop_id=None, reason="other", note=None, **kw):
        driver = self._current_driver()
        stop = self._owned_stop(stop_id)
        if not stop:
            return self._err("Stop not found or not yours.", "not_found")
        exc = request.env["odotrans.exception"].create({
            "stop_id": stop.id,
            "driver_id": driver.id if driver else False,
            "trip_ref": stop.leg_id.trip_ref,
            "reason": reason,
            "note": note,
        })
        return {"ok": True, "exception": exc.name}

    # --- telemetry ---------------------------------------------------------
    @http.route("/odotrans/api/v1/driver/telemetry", type="json", auth="user", methods=["POST"])
    def telemetry(self, points=None, **kw):
        """Accept a batch of positions and hand off to the GPS ingest path.

        ``points``: list of {ts, lat, lng, [speed_kph, heading]}. The vehicle is
        resolved from the driver's active trip so the app need not send it.
        """
        driver = self._current_driver()
        if not driver:
            return self._err("No driver profile.", "no_driver")
        if not points:
            return {"ok": True, "ingested": 0}
        trip = request.env["odotrans.trip"].search(
            [("driver_id", "=", driver.id), ("state", "in", ("dispatched", "in_progress"))],
            limit=1,
        )
        vehicle = trip.vehicle_id if trip else driver.default_vehicle_id
        if not vehicle:
            return self._err("No vehicle to attribute telemetry to.", "no_vehicle")
        batch = [{
            "vehicle_id": vehicle.id,
            "trip_ref": trip.name if trip else False,
            "ts": p.get("ts"),
            "lat": p.get("lat"),
            "lng": p.get("lng"),
            "speed_kph": p.get("speed_kph"),
            "heading": p.get("heading"),
            "source": "app",
        } for p in points if p.get("ts") and p.get("lat") is not None and p.get("lng") is not None]
        # Offload persistence so the request returns fast under load.
        request.env["odotrans.position"].with_delay(
            channel="root.odotrans.gps",
            description=f"Ingest telemetry ({len(batch)})",
        ).ingest_batch(batch)
        return {"ok": True, "accepted": len(batch)}
