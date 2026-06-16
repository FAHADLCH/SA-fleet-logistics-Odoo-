# -*- coding: utf-8 -*-
"""Waves and pick tasks for outbound / cross-dock processing.

A wave groups shipments to be processed together at a warehouse (released to
the floor as a batch). Each wave generates pick tasks; once picking completes
the wave is ready to load, which is the hand-off point to dispatch/route.

This is intentionally a lightweight orchestration layer over Odoo ``stock`` —
it coordinates *which* freight moves together and *when*, while inventory moves
remain in standard stock pickings.
"""
from odoo import api, fields, models
from odoo.exceptions import UserError


class OdotransWave(models.Model):
    _name = "odotrans.wave"
    _description = "ODOTRANS Wave"
    _inherit = ["odotrans.state.mixin", "odotrans.async.mixin", "mail.thread"]
    _order = "scheduled_date desc, id desc"

    _odotrans_state_field = "state"
    _odotrans_transitions = {
        "draft": ["released", "cancelled"],
        "released": ["picking", "cancelled"],
        "picking": ["ready", "cancelled"],
        "ready": ["loaded", "cancelled"],
        "loaded": ["done"],
    }

    name = fields.Char(required=True, copy=False, readonly=True, default="New", index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    warehouse_id = fields.Many2one("stock.warehouse", required=True, index=True)
    dock_id = fields.Many2one(
        "odotrans.dock", domain="[('warehouse_id','=',warehouse_id)]",
    )
    wave_type = fields.Selection(
        [("outbound", "Outbound"), ("crossdock", "Cross-dock")],
        default="outbound", required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("released", "Released"),
            ("picking", "Picking"),
            ("ready", "Ready to Load"),
            ("loaded", "Loaded"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True, index=True,
    )
    scheduled_date = fields.Datetime(default=fields.Datetime.now, index=True)
    shipment_ids = fields.Many2many("odotrans.shipment", string="Shipments")
    task_ids = fields.One2many("odotrans.pick.task", "wave_id", string="Pick Tasks")
    shipment_count = fields.Integer(compute="_compute_counts")
    task_progress = fields.Float(compute="_compute_counts", string="Pick Progress (%)")

    @api.depends("shipment_ids", "task_ids.state")
    def _compute_counts(self):
        for wave in self:
            wave.shipment_count = len(wave.shipment_ids)
            total = len(wave.task_ids)
            done = len(wave.task_ids.filtered(lambda t: t.state == "done"))
            wave.task_progress = (done / total * 100.0) if total else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odotrans.wave") or "New"
        return super().create(vals_list)

    def action_release(self):
        for wave in self:
            if not wave.shipment_ids:
                raise UserError(f"Wave {wave.name} has no shipments to release.")
            wave._transition_to("released")
            wave._generate_pick_tasks()
            wave._transition_to("picking")
        return True

    def _generate_pick_tasks(self):
        Task = self.env["odotrans.pick.task"]
        for wave in self:
            seq = 10
            for shipment in wave.shipment_ids:
                Task.create({
                    "wave_id": wave.id,
                    "shipment_id": shipment.id,
                    "sequence": seq,
                })
                seq += 10

    def action_mark_ready(self):
        for wave in self:
            if wave.task_ids and any(t.state != "done" for t in wave.task_ids):
                raise UserError(f"Wave {wave.name}: not all pick tasks are done.")
            wave._transition_to("ready")
        return True

    def action_load(self):
        for wave in self:
            wave._transition_to("loaded")
            if wave.dock_id:
                wave.dock_id.action_occupy()
            self.env["odotrans.event.bus"].emit(
                topic="warehouse.wave_loaded",
                payload={"wave_id": wave.id, "shipment_ids": wave.shipment_ids.ids},
                source_model=self._name, source_res_id=wave.id,
            )
        return True

    def action_done(self):
        for wave in self:
            wave._transition_to("done")
            if wave.dock_id:
                wave.dock_id.action_free()
        return True


class OdotransPickTask(models.Model):
    _name = "odotrans.pick.task"
    _description = "ODOTRANS Pick Task"
    _order = "wave_id, sequence, id"

    name = fields.Char(compute="_compute_name", store=True)
    wave_id = fields.Many2one("odotrans.wave", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="wave_id.company_id", store=True, index=True)
    sequence = fields.Integer(default=10)
    shipment_id = fields.Many2one("odotrans.shipment", required=True, index=True)
    bay_id = fields.Many2one("odotrans.bay")
    state = fields.Selection(
        [("todo", "To Do"), ("in_progress", "In Progress"), ("done", "Done")],
        default="todo", required=True, index=True,
    )

    @api.depends("wave_id.name", "sequence")
    def _compute_name(self):
        for task in self:
            task.name = f"{task.wave_id.name or '?'}/T{task.sequence}"

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})
