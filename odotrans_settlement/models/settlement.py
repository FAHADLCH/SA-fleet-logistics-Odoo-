# -*- coding: utf-8 -*-
"""Settlement runs and pay statements.

Flow:
  * A trip completing emits ``odotrans_trip.completed``. The settlement context
    subscribes and accrues a ``odotrans.settlement.accrual`` (a settleable item)
    on the billing-adjacent ``settlement`` channel — this is the durable backlog
    of "work done but not yet paid".
  * A ``odotrans.settlement.run`` for a period sweeps open accruals, groups them
    by payee into ``odotrans.pay.statement`` records with lines, and (optionally)
    posts vendor bills via ``account.move`` so payables live in core Accounting.

Keeping accrual creation event-driven and statement generation batch keeps the
hot path (trip completion) cheap while still supporting 50k+ trips/day.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OdotransSettlementAccrual(models.Model):
    _name = "odotrans.settlement.accrual"
    _description = "ODOTRANS Settlement Accrual"
    _inherit = ["odotrans.async.mixin"]
    _order = "trip_date desc, id desc"

    _odotrans_channel = "root.odotrans.settlement"

    name = fields.Char(default="New", readonly=True, copy=False)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    trip_id = fields.Many2one("odotrans.trip", required=True, ondelete="cascade", index=True)
    driver_id = fields.Many2one(related="trip_id.driver_id", store=True, index=True)
    trip_date = fields.Datetime(related="trip_id.actual_end", store=True)
    distance_km = fields.Float(readonly=True)
    amount = fields.Monetary(readonly=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id, required=True,
    )
    state = fields.Selection(
        [("open", "Open"), ("settled", "Settled"), ("void", "Void")],
        default="open", required=True, index=True,
    )
    statement_id = fields.Many2one("odotrans.pay.statement", readonly=True, index=True)

    _sql_constraints = [
        ("unique_trip", "unique(trip_id)", "This trip already has a settlement accrual."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.settlement.accrual") or "New"
        return super().create(vals_list)

    @api.model
    def _odotrans_on_trip_completed(self, event):
        """Accrue payable work when a trip completes (idempotent per trip)."""
        trip_id = (event.payload or {}).get("id")
        if not trip_id:
            return
        trip = self.env["odotrans.trip"].browse(trip_id).exists()
        if not trip or not trip.driver_id:
            return
        if self.search_count([("trip_id", "=", trip.id)]):
            return  # already accrued
        rule = self.env["odotrans.pay.rule"].find_for(trip)
        if not rule:
            return
        distance_km = self._trip_distance_km(trip)
        self.create({
            "trip_id": trip.id,
            "distance_km": distance_km,
            "amount": rule.compute_pay(trip, distance_km=distance_km),
        })

    def _trip_distance_km(self, trip):
        run = self.env["odotrans.optimization.run"].search(
            [("trip_id", "=", trip.id), ("distance_m", ">", 0)], limit=1, order="id desc",
        )
        return (run.distance_m / 1000.0) if run else 0.0


class OdotransSettlementRun(models.Model):
    _name = "odotrans.settlement.run"
    _description = "ODOTRANS Settlement Run"
    _inherit = ["odotrans.state.mixin", "odotrans.async.mixin", "mail.thread"]
    _order = "date_to desc, id desc"

    _odotrans_channel = "root.odotrans.settlement"
    _odotrans_state_field = "state"
    _odotrans_transitions = {
        "draft": ["computing", "cancelled"],
        "computing": ["computed", "cancelled"],
        "computed": ["posted", "cancelled"],
        "posted": [],
    }

    name = fields.Char(default="New", readonly=True, copy=False, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    date_from = fields.Date(required=True, default=lambda s: fields.Date.context_today(s).replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    state = fields.Selection(
        [("draft", "Draft"), ("computing", "Computing"), ("computed", "Computed"),
         ("posted", "Posted"), ("cancelled", "Cancelled")],
        default="draft", required=True, tracking=True, index=True,
    )
    statement_ids = fields.One2many("odotrans.pay.statement", "run_id", string="Pay Statements")
    statement_count = fields.Integer(compute="_compute_totals")
    total_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id, required=True,
    )

    @api.depends("statement_ids.amount")
    def _compute_totals(self):
        for run in self:
            run.statement_count = len(run.statement_ids)
            run.total_amount = sum(run.statement_ids.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.settlement.run") or "New"
        return super().create(vals_list)

    def action_compute(self):
        """Enqueue accrual sweep on the settlement channel."""
        for run in self:
            run._transition_to("computing")
            run._enqueue(
                "_compute_statements",
                channel="root.odotrans.settlement",
                description=f"Compute settlement {run.name}",
                idempotency_key=f"settle-{run.id}",
            )
        return True

    def _compute_statements(self):
        """Group open accruals in the period into pay statements per driver."""
        self.ensure_one()
        self.statement_ids.unlink()
        accruals = self.env["odotrans.settlement.accrual"].search([
            ("state", "=", "open"),
            ("company_id", "=", self.company_id.id),
            ("trip_date", ">=", fields.Datetime.to_datetime(self.date_from)),
            ("trip_date", "<=", fields.Datetime.to_datetime(self.date_to).replace(hour=23, minute=59, second=59)),
        ])
        Statement = self.env["odotrans.pay.statement"]
        by_driver = {}
        for accrual in accruals:
            by_driver.setdefault(accrual.driver_id, self.env["odotrans.settlement.accrual"])
            by_driver[accrual.driver_id] |= accrual
        for driver, items in by_driver.items():
            statement = Statement.create({
                "run_id": self.id,
                "driver_id": driver.id,
                "line_ids": [
                    (0, 0, {
                        "accrual_id": a.id,
                        "trip_id": a.trip_id.id,
                        "amount": a.amount,
                    }) for a in items
                ],
            })
            items.write({"state": "settled", "statement_id": statement.id})
        self._transition_to("computed")

    def action_post(self):
        """Mark statements posted (vendor-bill creation left as opt-in hook)."""
        for run in self:
            if run.state != "computed":
                raise UserError("Run must be computed before posting.")
            run.statement_ids.write({"state": "posted"})
            run._transition_to("posted")
        return True

    def action_cancel(self):
        for run in self:
            run.statement_ids.mapped("line_ids.accrual_id").write({"state": "open", "statement_id": False})
            run.statement_ids.unlink()
            run._transition_to("cancelled")


class OdotransPayStatement(models.Model):
    _name = "odotrans.pay.statement"
    _description = "ODOTRANS Pay Statement"
    _order = "run_id, id"

    name = fields.Char(default="New", readonly=True, copy=False)
    run_id = fields.Many2one("odotrans.settlement.run", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="run_id.company_id", store=True, index=True)
    driver_id = fields.Many2one("odotrans.driver", required=True, index=True)
    line_ids = fields.One2many("odotrans.pay.statement.line", "statement_id", string="Lines")
    amount = fields.Monetary(compute="_compute_amount", store=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="run_id.currency_id", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted")], default="draft", required=True, index=True,
    )

    @api.depends("line_ids.amount")
    def _compute_amount(self):
        for stmt in self:
            stmt.amount = sum(stmt.line_ids.mapped("amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.pay.statement") or "New"
        return super().create(vals_list)


class OdotransPayStatementLine(models.Model):
    _name = "odotrans.pay.statement.line"
    _description = "ODOTRANS Pay Statement Line"
    _order = "statement_id, id"

    statement_id = fields.Many2one(
        "odotrans.pay.statement", required=True, ondelete="cascade", index=True,
    )
    accrual_id = fields.Many2one("odotrans.settlement.accrual", required=True, ondelete="restrict")
    trip_id = fields.Many2one("odotrans.trip", required=True, index=True)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="statement_id.currency_id", store=True)
