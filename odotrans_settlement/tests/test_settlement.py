# -*- coding: utf-8 -*-
"""Settlement: accrual on trip completion and run -> statement aggregation.

The trip is walked to ``completed`` via the FSM directly so the test does not
depend on the full dispatch flow (vehicles, stops). The accrual handler and the
settlement run are then invoked synchronously.
"""
from odoo.tests.common import TransactionCase


class TestSettlement(TransactionCase):
    def setUp(self):
        super().setUp()
        self.driver = self.env["odotrans.driver"].create({"name": "Jane Driver"})
        self.Rule = self.env["odotrans.pay.rule"]
        self.Accrual = self.env["odotrans.settlement.accrual"]
        self.Run = self.env["odotrans.settlement.run"]

    def _completed_trip(self):
        trip = self.env["odotrans.trip"].create({"driver_id": self.driver.id})
        # Walk the FSM to completed without the dispatch action guards.
        for state in ("assigned", "dispatched", "in_progress", "completed"):
            trip._transition_to(state)
        return trip

    def _fake_event(self, trip):
        return self.env["odotrans.event"].create({
            "topic": "odotrans_trip.completed",
            "payload": {"id": trip.id, "to": "completed"},
            "source_model": "odotrans.trip",
            "source_res_id": trip.id,
        })

    def test_no_rule_no_accrual(self):
        trip = self._completed_trip()
        self.Accrual._odotrans_on_trip_completed(self._fake_event(trip))
        self.assertFalse(self.Accrual.search([("trip_id", "=", trip.id)]))

    def test_accrual_created_with_per_trip_pay(self):
        self.Rule.create({"name": "flat", "per_trip": 120.0})
        trip = self._completed_trip()
        self.Accrual._odotrans_on_trip_completed(self._fake_event(trip))
        accrual = self.Accrual.search([("trip_id", "=", trip.id)])
        self.assertEqual(len(accrual), 1)
        self.assertAlmostEqual(accrual.amount, 120.0, places=2)
        self.assertEqual(accrual.state, "open")

    def test_accrual_is_idempotent_per_trip(self):
        self.Rule.create({"name": "flat", "per_trip": 100.0})
        trip = self._completed_trip()
        event = self._fake_event(trip)
        self.Accrual._odotrans_on_trip_completed(event)
        self.Accrual._odotrans_on_trip_completed(event)
        self.assertEqual(
            self.Accrual.search_count([("trip_id", "=", trip.id)]), 1,
        )

    def test_run_groups_accruals_into_statements(self):
        self.Rule.create({"name": "flat", "per_trip": 75.0})
        trip_a = self._completed_trip()
        trip_b = self._completed_trip()
        self.Accrual._odotrans_on_trip_completed(self._fake_event(trip_a))
        self.Accrual._odotrans_on_trip_completed(self._fake_event(trip_b))

        run = self.Run.create({})
        run._transition_to("computing")
        run._compute_statements()

        self.assertEqual(run.state, "computed")
        self.assertEqual(len(run.statement_ids), 1)  # both trips -> same driver
        statement = run.statement_ids
        self.assertEqual(statement.driver_id, self.driver)
        self.assertAlmostEqual(statement.amount, 150.0, places=2)
        # Accruals are now settled and linked.
        self.assertEqual(
            set(self.Accrual.browse(
                (trip_a + trip_b).mapped("id")
            ).mapped("trip_id.id")),
            {trip_a.id, trip_b.id},
        )
        settled = self.Accrual.search([("trip_id", "in", (trip_a + trip_b).ids)])
        self.assertEqual(settled.mapped("state"), ["settled", "settled"])

    def test_cancel_run_reopens_accruals(self):
        self.Rule.create({"name": "flat", "per_trip": 60.0})
        trip = self._completed_trip()
        self.Accrual._odotrans_on_trip_completed(self._fake_event(trip))
        run = self.Run.create({})
        run._transition_to("computing")
        run._compute_statements()
        run.action_cancel()
        accrual = self.Accrual.search([("trip_id", "=", trip.id)])
        self.assertEqual(accrual.state, "open")
        self.assertFalse(accrual.statement_id)
