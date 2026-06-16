# -*- coding: utf-8 -*-
"""Maintenance: PM due detection, work-order grounding, defect escalation.

Uses a minimal fleet vehicle. Work-order start/complete is asserted via the
vehicle's ``odotrans_status`` and the emitted ``maintenance.vehicle_*`` events.
"""
from odoo.tests.common import TransactionCase


class TestMaintenance(TransactionCase):
    def setUp(self):
        super().setUp()
        brand = self.env["fleet.vehicle.model.brand"].create({"name": "TestBrand"})
        model = self.env["fleet.vehicle.model"].create({
            "name": "TestModel", "brand_id": brand.id,
        })
        self.vehicle = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "odotrans_enabled": True,
            "odotrans_status": "available",
        })
        self.Plan = self.env["odotrans.pm.plan"]
        self.WO = self.env["odotrans.work.order"]
        self.Defect = self.env["odotrans.defect"]
        self.Event = self.env["odotrans.event"]

    # --- PM plans ----------------------------------------------------------
    def test_plan_due_by_distance_generates_work_order(self):
        self.vehicle.odometer = 10000.0
        self.Plan.create({
            "name": "oil", "vehicle_id": self.vehicle.id,
            "service_type": "oil", "interval_km": 5000.0,
            "last_service_odometer": 4000.0,  # next due at 9000 -> due
        })
        self.Plan.cron_generate_due_work_orders()
        wo = self.WO.search([("vehicle_id", "=", self.vehicle.id)])
        self.assertEqual(len(wo), 1)
        self.assertEqual(wo.order_type, "preventive")

    def test_plan_not_due_creates_nothing(self):
        self.vehicle.odometer = 5000.0
        self.Plan.create({
            "name": "oil", "vehicle_id": self.vehicle.id,
            "interval_km": 5000.0, "last_service_odometer": 4000.0,  # due at 9000
        })
        self.Plan.cron_generate_due_work_orders()
        self.assertFalse(self.WO.search([("vehicle_id", "=", self.vehicle.id)]))

    def test_cron_does_not_duplicate_open_work_order(self):
        self.vehicle.odometer = 10000.0
        plan = self.Plan.create({
            "name": "oil", "vehicle_id": self.vehicle.id,
            "interval_km": 5000.0, "last_service_odometer": 4000.0,
        })
        self.Plan.cron_generate_due_work_orders()
        self.Plan.cron_generate_due_work_orders()
        self.assertEqual(
            self.WO.search_count([("plan_id", "=", plan.id)]), 1,
        )

    # --- work order lifecycle ---------------------------------------------
    def test_start_grounds_vehicle_and_emits_down(self):
        wo = self.WO.create({"vehicle_id": self.vehicle.id, "service_type": "brakes"})
        before = self.Event.search_count([("topic", "=", "maintenance.vehicle_down")])
        wo.action_start()
        self.assertEqual(wo.state, "in_progress")
        after = self.Event.search_count([("topic", "=", "maintenance.vehicle_down")])
        self.assertEqual(after, before + 1)

    def test_complete_restores_vehicle_and_emits_up(self):
        # Manually ground the vehicle (simulates the fleet handler reaction).
        self.vehicle.odotrans_status = "maintenance"
        wo = self.WO.create({"vehicle_id": self.vehicle.id})
        wo.action_start()
        wo.action_done()
        self.assertEqual(wo.state, "done")
        self.assertEqual(self.vehicle.odotrans_status, "available")
        self.assertTrue(self.Event.search_count(
            [("topic", "=", "maintenance.vehicle_up"), ("source_res_id", "=", wo.id)]
        ))

    def test_complete_updates_plan_last_service(self):
        self.vehicle.odometer = 12000.0
        plan = self.Plan.create({
            "name": "oil", "vehicle_id": self.vehicle.id, "interval_km": 5000.0,
        })
        wo = self.WO.create({
            "vehicle_id": self.vehicle.id, "plan_id": plan.id, "order_type": "preventive",
        })
        wo.action_start()
        wo.action_done()
        self.assertAlmostEqual(plan.last_service_odometer, 12000.0, places=2)

    # --- defects -----------------------------------------------------------
    def test_critical_defect_emits_vehicle_down(self):
        before = self.Event.search_count([("topic", "=", "maintenance.vehicle_down")])
        self.Defect.create({
            "vehicle_id": self.vehicle.id, "severity": "critical",
            "description": "Brake failure",
        })
        after = self.Event.search_count([("topic", "=", "maintenance.vehicle_down")])
        self.assertEqual(after, before + 1)

    def test_low_defect_does_not_emit(self):
        before = self.Event.search_count([("topic", "=", "maintenance.vehicle_down")])
        self.Defect.create({
            "vehicle_id": self.vehicle.id, "severity": "low",
            "description": "Scratch",
        })
        after = self.Event.search_count([("topic", "=", "maintenance.vehicle_down")])
        self.assertEqual(after, before)

    def test_defect_escalation_creates_work_order(self):
        defect = self.Defect.create({
            "vehicle_id": self.vehicle.id, "severity": "high",
            "description": "Noise",
        })
        action = defect.action_create_work_order()
        self.assertTrue(defect.work_order_id)
        self.assertEqual(defect.state, "in_progress")
        self.assertEqual(defect.work_order_id.order_type, "corrective")
        self.assertEqual(action["res_model"], "odotrans.work.order")
