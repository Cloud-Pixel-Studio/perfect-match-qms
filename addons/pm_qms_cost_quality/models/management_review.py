from odoo import fields, models


class PmQmsManagementReviewInput(models.Model):
    _inherit = "pm.qms.management.review.input"

    category = fields.Selection(selection_add=[("cost_quality", "Cost of Quality")], ondelete={"cost_quality": "cascade"})
    source_type = fields.Selection(selection_add=[("cost_quality_event", "Cost of Quality Event")], ondelete={"cost_quality_event": "cascade"})


class PmQmsManagementReview(models.Model):
    _inherit = "pm.qms.management.review"

    def _generate_snapshot_inputs(self, snapshot_date):
        result = super()._generate_snapshot_inputs(snapshot_date)
        for review in self:
            review._snapshot_cost_quality(snapshot_date)
        return result

    def _snapshot_cost_quality(self, snapshot_date):
        Event = self.env["pm.qms.cost.event"]
        domain = [
            ("company_id", "=", self.company_id.id),
            ("organization_id", "=", self.organization_id.id),
            ("event_date", ">=", self.period_start),
            ("event_date", "<=", self.period_end),
            ("state", "=", "confirmed"),
        ]
        events = Event.search(domain, order="event_date, code")
        total = sum(events.mapped("quality_cost_total"))
        copq = sum(events.mapped("copq_amount"))
        self._create_input(
            "cost_quality",
            f"Cost of Quality summary for {self.period_start} to {self.period_end}",
            snapshot_date=snapshot_date,
            status_snapshot="confirmed_events" if events else "no_confirmed_events",
            numeric_value=copq,
            unit_of_measure=self.company_id.currency_id.name,
            source_type="cost_quality_event",
            source_identifier="confirmed_cost_quality_events",
            description="Official Cost of Quality snapshot excludes draft and cancelled cost events.",
            text_value=f"Confirmed events: {len(events)}; total quality cost: {total:.2f}; COPQ: {copq:.2f}",
        )
        for event in events:
            self._create_input(
                "cost_quality",
                f"{event.code} - {event.name}",
                snapshot_date=snapshot_date,
                status_snapshot=event.state,
                numeric_value=event.copq_amount,
                unit_of_measure=event.currency_id.name,
                source_type="cost_quality_event",
                source_identifier=event.code,
                description=event.notes,
                text_value=(
                    f"Quality cost: {event.quality_cost_total:.2f}; recovery: {event.recovery_total:.2f}; "
                    f"net: {event.net_quality_cost:.2f}; COPQ: {event.copq_amount:.2f}; "
                    f"source: {event.source_identifier or 'none'}"
                ),
            )
