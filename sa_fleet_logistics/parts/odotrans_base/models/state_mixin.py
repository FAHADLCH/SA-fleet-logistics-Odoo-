# -*- coding: utf-8 -*-
"""Finite state machine mixin.

Domain aggregates (shipment, trip, work order ...) declare their allowed
transitions once and inherit guarded state changes plus automatic domain-event
emission. This keeps lifecycle rules in one place instead of scattered writes.

Concrete models override the two class attributes::

    class OdotransShipment(models.Model):
        _name = "odotrans.shipment"
        _inherit = ["odotrans.state.mixin", "mail.thread"]

        _odotrans_state_field = "state"
        _odotrans_transitions = {
            "draft": ["confirmed", "cancelled"],
            "confirmed": ["planned", "cancelled"],
            "planned": ["in_transit", "cancelled"],
            "in_transit": ["delivered", "exception"],
            "delivered": ["closed"],
        }
"""
from odoo import models
from odoo.exceptions import UserError


class OdotransStateMixin(models.AbstractModel):
    _name = "odotrans.state.mixin"
    _description = "ODOTRANS State Machine Mixin"

    # Name of the Selection field holding the lifecycle state.
    _odotrans_state_field = "state"
    # Mapping {current_state: [allowed_next_states]}.
    _odotrans_transitions = {}

    def _allowed_targets(self, current):
        return self._odotrans_transitions.get(current, [])

    def _transition_to(self, target, payload=None):
        """Guarded state change. Emits ``<model>.<target>`` on success.

        :param target: destination state value.
        :param payload: optional dict merged into the emitted event payload.
        """
        field = self._odotrans_state_field
        for record in self:
            current = record[field]
            if current == target:
                continue
            if target not in record._allowed_targets(current):
                raise UserError(
                    f"Illegal transition {current!r} -> {target!r} on "
                    f"{record._name} (id={record.id})."
                )
            record[field] = target
            topic = f"{record._name.replace('.', '_')}.{target}"
            event_payload = {"id": record.id, "from": current, "to": target}
            if payload:
                event_payload.update(payload)
            record.env["odotrans.event.bus"].emit(
                topic=topic,
                payload=event_payload,
                source_model=record._name,
                source_res_id=record.id,
            )
        return True
