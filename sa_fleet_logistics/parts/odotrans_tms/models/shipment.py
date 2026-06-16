# -*- coding: utf-8 -*-
"""Shipment aggregate root — the heart of the TMS context.

A shipment is the customer-facing transport order. Its lifecycle is governed by
the shared FSM mixin; every transition emits a domain event that other contexts
(dispatch, billing, settlement) subscribe to asynchronously. Heavy work
(geocoding, optimization hand-off) is pushed to queue_job via the async mixin.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OdotransShipment(models.Model):
    _name = "odotrans.shipment"
    _description = "ODOTRANS Shipment"
    _inherit = ["odotrans.state.mixin", "odotrans.async.mixin", "mail.thread", "mail.activity.mixin"]
    _order = "priority desc, sla_due asc, id desc"

    _odotrans_state_field = "state"
    _odotrans_transitions = {
        "draft": ["confirmed", "cancelled"],
        "confirmed": ["planned", "cancelled"],
        "planned": ["in_transit", "cancelled"],
        "in_transit": ["delivered", "exception"],
        "exception": ["in_transit", "delivered", "cancelled"],
        "delivered": ["closed"],
    }
    _odotrans_channel = "root.odotrans.default"

    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda self: "New",
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    customer_id = fields.Many2one(
        "res.partner", string="Customer", required=True, tracking=True, index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("planned", "Planned"),
            ("in_transit", "In Transit"),
            ("exception", "Exception"),
            ("delivered", "Delivered"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True, index=True,
    )
    service_level = fields.Selection(
        [("economy", "Economy"), ("standard", "Standard"), ("express", "Express"), ("same_day", "Same Day")],
        default="standard", required=True, tracking=True,
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "High"), ("2", "Urgent")], default="0", index=True,
    )

    origin_partner_id = fields.Many2one("res.partner", string="Origin")
    dest_partner_id = fields.Many2one("res.partner", string="Destination")
    origin_lat = fields.Float(digits=(10, 7))
    origin_lng = fields.Float(digits=(10, 7))
    dest_lat = fields.Float(digits=(10, 7))
    dest_lng = fields.Float(digits=(10, 7))

    weight_kg = fields.Float(string="Weight (kg)")
    volume_m3 = fields.Float(string="Volume (m³)")
    package_count = fields.Integer(string="Packages", default=1)

    sla_due = fields.Datetime(string="SLA Due", tracking=True)
    requested_date = fields.Datetime(default=fields.Datetime.now)

    leg_ids = fields.One2many("odotrans.leg", "shipment_id", string="Legs")
    leg_count = fields.Integer(compute="_compute_counts")
    stop_count = fields.Integer(compute="_compute_counts")

    # Cross-context references stored as soft links (id + model) to avoid hard
    # coupling; resolved lazily by the owning context's views.
    trip_ref = fields.Char(string="Trip Reference", readonly=True, copy=False)
    is_late = fields.Boolean(compute="_compute_is_late", search="_search_is_late")

    @api.depends("leg_ids", "leg_ids.stop_ids")
    def _compute_counts(self):
        for ship in self:
            ship.leg_count = len(ship.leg_ids)
            ship.stop_count = sum(len(leg.stop_ids) for leg in ship.leg_ids)

    @api.depends("sla_due", "state")
    def _compute_is_late(self):
        now = fields.Datetime.now()
        for ship in self:
            open_states = ("confirmed", "planned", "in_transit", "exception")
            ship.is_late = bool(ship.sla_due and ship.sla_due < now and ship.state in open_states)

    def _search_is_late(self, operator, value):
        now = fields.Datetime.now()
        open_states = ("confirmed", "planned", "in_transit", "exception")
        domain = [("sla_due", "<", now), ("state", "in", open_states)]
        if (operator == "=" and not value) or (operator == "!=" and value):
            return ["!", "&"] + domain[:1] + ["&"] + domain[1:]
        return domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.shipment") or "New"
        return super().create(vals_list)

    # --- lifecycle actions -------------------------------------------------
    def action_confirm(self):
        for ship in self:
            if not ship.leg_ids:
                ship._build_default_leg()
            ship._transition_to("confirmed")
            ship._enqueue(
                "_geocode_endpoints",
                channel="root.odotrans.default",
                description=f"Geocode {ship.name}",
                idempotency_key=f"geocode:{ship.name}",
            )
        return True

    def action_plan(self):
        self._transition_to("planned")

    def action_start_transit(self):
        self._transition_to("in_transit")

    def action_deliver(self):
        self._transition_to("delivered")

    def action_close(self):
        self._transition_to("closed")

    def action_cancel(self):
        self._transition_to("cancelled")

    def action_flag_exception(self, reason=False):
        self._transition_to("exception", payload={"reason": reason} if reason else None)

    def _build_default_leg(self):
        """Single direct leg with pickup + drop stops from shipment endpoints."""
        self.ensure_one()
        leg = self.env["odotrans.leg"].create({
            "shipment_id": self.id,
            "sequence": 10,
            "mode": "road",
        })
        self.env["odotrans.stop"].create([
            {
                "leg_id": leg.id, "sequence": 10, "stop_type": "pickup",
                "partner_id": self.origin_partner_id.id or False,
                "lat": self.origin_lat, "lng": self.origin_lng,
            },
            {
                "leg_id": leg.id, "sequence": 20, "stop_type": "drop",
                "partner_id": self.dest_partner_id.id or False,
                "lat": self.dest_lat, "lng": self.dest_lng,
            },
        ])
        return leg

    # --- async jobs --------------------------------------------------------
    def _geocode_endpoints(self):
        """Resolve missing coordinates via the configured map provider."""
        Map = self.env["odotrans.map"]
        for ship in self:
            if ship.origin_partner_id and not (ship.origin_lat and ship.origin_lng):
                geo = Map.geocode(ship.origin_partner_id.contact_address or ship.origin_partner_id.name)
                if geo:
                    ship.origin_lat, ship.origin_lng = geo["lat"], geo["lng"]
            if ship.dest_partner_id and not (ship.dest_lat and ship.dest_lng):
                geo = Map.geocode(ship.dest_partner_id.contact_address or ship.dest_partner_id.name)
                if geo:
                    ship.dest_lat, ship.dest_lng = geo["lat"], geo["lng"]
            ship._sync_stop_coordinates()
        return True

    def _sync_stop_coordinates(self):
        for ship in self:
            for leg in ship.leg_ids:
                for stop in leg.stop_ids:
                    if stop.stop_type == "pickup" and not (stop.lat and stop.lng):
                        stop.lat, stop.lng = ship.origin_lat, ship.origin_lng
                    elif stop.stop_type == "drop" and not (stop.lat and stop.lng):
                        stop.lat, stop.lng = ship.dest_lat, ship.dest_lng

    # --- event handler (subscribed via data record) -----------------------
    @api.model
    def _odotrans_on_pod_delivered(self, event):
        """React to a delivery-proof completion: mark shipment delivered."""
        payload = event.payload or {}
        shipment_id = payload.get("shipment_id")
        if not shipment_id:
            return
        ship = self.browse(shipment_id).exists()
        if ship and ship.state in ("in_transit", "exception"):
            ship.action_deliver()
