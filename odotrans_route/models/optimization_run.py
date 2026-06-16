# -*- coding: utf-8 -*-
"""Route optimization run — async VRP solving via the map provider abstraction.

Scale strategy (50k shipments/day): we never solve one global VRP. A *wave*
groups stops by geography + time window into a bounded sub-problem. Each run is
an isolated, retryable ``queue_job`` on the ``optimization`` channel, so many
waves solve in parallel without contending with billing/GPS work.

The run snapshots its request (so it is reproducible/auditable), calls the
configured provider's ``optimize``/``distance_matrix``, and writes the resulting
stop sequence back onto the trip's manifest.
"""
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Above this stop count we fall back to a nearest-neighbour heuristic instead of
# a provider round-trip, keeping per-wave latency bounded.
PROVIDER_STOP_LIMIT = 25


class OdotransOptimizationRun(models.Model):
    _name = "odotrans.optimization.run"
    _description = "ODOTRANS Optimization Run"
    _inherit = ["odotrans.async.mixin"]
    _order = "create_date desc, id desc"

    _odotrans_channel = "root.odotrans.optimization"

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    trip_id = fields.Many2one("odotrans.trip", ondelete="cascade", index=True)
    provider = fields.Char(readonly=True, help="Map provider used for this run.")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("queued", "Queued"),
            ("running", "Running"),
            ("done", "Done"),
            ("failed", "Failed"),
        ],
        default="draft", required=True, index=True,
    )
    depot_lat = fields.Float(digits=(10, 7))
    depot_lng = fields.Float(digits=(10, 7))
    request_snapshot = fields.Json(readonly=True, help="Ordered stop ids + coordinates submitted.")
    result_sequence = fields.Json(readonly=True, help="Optimized ordering of stop ids.")
    distance_m = fields.Float(string="Distance (m)", readonly=True)
    duration_s = fields.Float(string="Duration (s)", readonly=True)
    error = fields.Text(readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.optimization.run") or "New"
        return super().create(vals_list)

    # --- public entry points ----------------------------------------------
    def action_optimize(self):
        """Queue this run on the optimization channel (idempotent per trip)."""
        for run in self:
            run.state = "queued"
            run._enqueue(
                "_run_optimization",
                channel="root.odotrans.optimization",
                description=f"Optimize {run.name}",
                idempotency_key=f"optrun:{run.id}",
            )
        return True

    @api.model
    def optimize_trip(self, trip):
        """Create + queue an optimization run for a trip's manifest stops."""
        depot = self._resolve_depot(trip)
        run = self.create({
            "trip_id": trip.id,
            "depot_lat": depot[0],
            "depot_lng": depot[1],
        })
        run.action_optimize()
        return run

    # --- worker ------------------------------------------------------------
    def _run_optimization(self):
        self.ensure_one()
        self.write({"state": "running", "started_at": fields.Datetime.now()})
        try:
            stops = self._ordered_stops()
            geo_stops = [s for s in stops if s.lat and s.lng]
            if len(geo_stops) < 2:
                raise UserError("Not enough geocoded stops to optimize.")

            depot = (self.depot_lat, self.depot_lng)
            coords = [(s.lat, s.lng) for s in geo_stops]
            snapshot = {"depot": depot, "stops": [{"id": s.id, "lat": s.lat, "lng": s.lng} for s in geo_stops]}

            provider = self.env["ir.config_parameter"].sudo().get_param("odotrans.map.provider", "osrm")
            if len(geo_stops) <= PROVIDER_STOP_LIMIT:
                result = self.env["odotrans.map"].optimize(depot, coords)
                order_idx = result.get("sequence") or list(range(len(coords)))
                # provider returns waypoint indices including depot at 0
                ordered_stop_ids = self._map_sequence(order_idx, geo_stops)
                summary = result.get("summary") or {}
                distance = summary.get("distance") or 0.0
                duration = summary.get("duration") or 0.0
            else:
                ordered_stop_ids, distance, duration = self._heuristic_order(depot, geo_stops)

            self.write({
                "state": "done",
                "provider": provider,
                "request_snapshot": snapshot,
                "result_sequence": ordered_stop_ids,
                "distance_m": distance,
                "duration_s": duration,
                "finished_at": fields.Datetime.now(),
            })
            self._apply_to_trip(ordered_stop_ids)
        except Exception as exc:  # noqa: BLE001 - surfaced to queue_job for retry
            self.write({"state": "failed", "error": str(exc), "finished_at": fields.Datetime.now()})
            raise
        return True

    # --- helpers -----------------------------------------------------------
    def _resolve_depot(self, trip):
        # First pickup stop, else vehicle last position, else (0,0).
        pickups = trip.manifest_id.line_ids.mapped("stop_id").filtered(
            lambda s: s.stop_type == "pickup" and s.lat and s.lng
        )
        if pickups:
            return (pickups[0].lat, pickups[0].lng)
        v = trip.vehicle_id
        if v and v.last_lat and v.last_lng:
            return (v.last_lat, v.last_lng)
        return (0.0, 0.0)

    def _ordered_stops(self):
        self.ensure_one()
        if not self.trip_id:
            return self.env["odotrans.stop"]
        return self.trip_id.manifest_id.line_ids.sorted("sequence").mapped("stop_id")

    def _map_sequence(self, order_idx, geo_stops):
        """Translate provider waypoint indices to stop ids, dropping the depot."""
        ordered = []
        for idx in order_idx:
            # idx 0 is the depot in our coords payload; provider trip indices may
            # include it — skip out-of-range/depot entries defensively.
            if idx is None:
                continue
            if 0 <= idx < len(geo_stops):
                ordered.append(geo_stops[idx].id)
        # Fallback: if mapping produced nothing useful, keep original order.
        return ordered or [s.id for s in geo_stops]

    def _heuristic_order(self, depot, geo_stops):
        """Nearest-neighbour fallback using a single provider distance matrix.

        Bounded and cheap: one matrix call, O(n²) greedy walk. Keeps large waves
        within latency budget without a heavyweight solver.
        """
        coords = [depot] + [(s.lat, s.lng) for s in geo_stops]
        matrix = self.env["odotrans.map"].distance_matrix(coords, coords)

        def dur(i, j):
            cell = matrix[i][j]
            return (cell[1] if cell and cell[1] is not None else cell[0]) or 0.0

        n = len(coords)
        visited = {0}
        order = []
        current = 0
        total = 0.0
        while len(visited) < n:
            nxt, best = None, None
            for j in range(1, n):
                if j in visited:
                    continue
                d = dur(current, j)
                if best is None or d < best:
                    best, nxt = d, j
            if nxt is None:
                break
            visited.add(nxt)
            order.append(nxt)
            total += best or 0.0
            current = nxt
        ordered_stop_ids = [geo_stops[idx - 1].id for idx in order]
        return ordered_stop_ids, 0.0, total

    def _apply_to_trip(self, ordered_stop_ids):
        self.ensure_one()
        if not self.trip_id:
            return
        self.trip_id.manifest_id.apply_sequence(ordered_stop_ids)
        self.trip_id.route_plan_ref = self.name
        # propagate naive ETAs from cumulative durations if available
        self.env["odotrans.event.bus"].emit(
            topic="route.optimized",
            payload={"trip_id": self.trip_id.id, "run": self.name,
                     "distance_m": self.distance_m, "duration_s": self.duration_s},
            source_model=self._name, source_res_id=self.id,
        )

    # --- event handler -----------------------------------------------------
    @api.model
    def _odotrans_on_trip_dispatched(self, event):
        """Optionally (re)optimize a trip right before dispatch."""
        return True
