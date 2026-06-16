# -*- coding: utf-8 -*-
"""GPS position ingest — the highest-volume path in ODOTRANS.

Design rules for 50k vehicles pinging frequently:

* The ``odotrans.position`` model is intentionally *thin*: no mail.thread, no
  audit, minimal indexes. It is meant to be partitioned by day at the database
  level (see repo notes) and archived/downsampled out of the hot path.
* Ingestion is **batched**. The driver app / telematics webhook posts arrays;
  the worker bulk-inserts via a single multi-row INSERT rather than per-record
  ORM ``create`` to keep throughput high.
* Only a tiny *snapshot* (last lat/lng/ts) is written back to the vehicle, so
  dashboards and dispatch read current location without scanning the trace.
"""
import logging

from psycopg2.extras import execute_values

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OdotransPosition(models.Model):
    _name = "odotrans.position"
    _description = "ODOTRANS Vehicle Position"
    _order = "ts desc"
    _log_access = False  # drop create/write uid+date columns — pure telemetry

    vehicle_id = fields.Many2one("fleet.vehicle", required=True, ondelete="cascade", index=True)
    trip_ref = fields.Char(index=True)
    ts = fields.Datetime(required=True, index=True)
    lat = fields.Float(digits=(10, 7), required=True)
    lng = fields.Float(digits=(10, 7), required=True)
    speed_kph = fields.Float()
    heading = fields.Float()
    source = fields.Selection(
        [("app", "Driver App"), ("telematics", "Telematics"), ("manual", "Manual")],
        default="app", index=True,
    )

    @api.model
    def ingest_batch(self, points):
        """Bulk-insert a batch of positions and update vehicle snapshots.

        :param points: list of dicts with keys
            vehicle_id, ts, lat, lng, [speed_kph, heading, source, trip_ref]
        Returns the number of rows inserted.
        """
        if not points:
            return 0
        rows = []
        latest = {}  # vehicle_id -> (ts, lat, lng)
        for p in points:
            vid = p["vehicle_id"]
            ts = p["ts"]
            lat = p["lat"]
            lng = p["lng"]
            rows.append((
                vid, p.get("trip_ref"), ts, lat, lng,
                p.get("speed_kph"), p.get("heading"), p.get("source", "app"),
            ))
            cur = latest.get(vid)
            if cur is None or ts > cur[0]:
                latest[vid] = (ts, lat, lng)

        # Single multi-row INSERT — far cheaper than ORM create at volume.
        self.env.cr.execute("SELECT 1 FROM odotrans_position LIMIT 0")  # ensure table exists
        execute_values(
            self.env.cr,
            """
            INSERT INTO odotrans_position
                (vehicle_id, trip_ref, ts, lat, lng, speed_kph, heading, source)
            VALUES %s
            """,
            rows,
            page_size=1000,
        )

        # Lightweight snapshot write-back (one UPDATE per vehicle in batch).
        for vid, (ts, lat, lng) in latest.items():
            self.env.cr.execute(
                """
                UPDATE fleet_vehicle
                   SET last_lat = %s, last_lng = %s, last_position_ts = %s
                 WHERE id = %s
                """,
                (lat, lng, ts, vid),
            )

        # Geofence evaluation is offloaded so ingest stays fast.
        self.env["odotrans.geofence"].with_delay(
            channel="root.odotrans.gps",
            description="Evaluate geofences for ingest batch",
        ).evaluate_snapshot(list(latest.keys()))
        return len(rows)
