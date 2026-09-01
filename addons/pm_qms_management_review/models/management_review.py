from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsManagementReview(models.Model):
    _name = "pm.qms.management.review"
    _description = "Perfect Match QMS Management Review"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "period_end desc, code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    active = fields.Boolean(default=True)

    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    planned_date = fields.Date(tracking=True)
    actual_date = fields.Date(tracking=True)
    chair_id = fields.Many2one("res.users", tracking=True)
    participant_ids = fields.Many2many(
        "res.users",
        "pm_qms_management_review_participant_rel",
        "review_id",
        "user_id",
        string="Participants",
    )

    objective = fields.Text()
    agenda_notes = fields.Text()
    general_notes = fields.Text()
    conclusion = fields.Text(string="Management Conclusion")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("preparing", "Preparing"),
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    snapshot_date = fields.Datetime(readonly=True)
    completed_date = fields.Datetime(readonly=True)
    next_review_date = fields.Date(tracking=True)

    input_ids = fields.One2many("pm.qms.management.review.input", "review_id", string="Review Inputs")
    decision_ids = fields.One2many("pm.qms.management.review.decision", "review_id", string="Decisions")
    action_ids = fields.One2many("pm.qms.management.review.action", "review_id", string="Actions")

    objective_input_count = fields.Integer(compute="_compute_summary_counts")
    kpi_input_count = fields.Integer(compute="_compute_summary_counts")
    kpi_off_target_count = fields.Integer(compute="_compute_summary_counts")
    customer_issue_count = fields.Integer(compute="_compute_summary_counts")
    supplier_issue_count = fields.Integer(compute="_compute_summary_counts")
    audits_reviewed_count = fields.Integer(compute="_compute_summary_counts")
    open_finding_count = fields.Integer(compute="_compute_summary_counts")
    high_risk_count = fields.Integer(compute="_compute_summary_counts")
    open_ncr_count = fields.Integer(compute="_compute_summary_counts")
    open_capa_count = fields.Integer(compute="_compute_summary_counts")
    previous_action_count = fields.Integer(compute="_compute_summary_counts")
    decision_count = fields.Integer(compute="_compute_summary_counts")
    open_action_count = fields.Integer(compute="_compute_summary_counts")

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Management review code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.management.review") or "PM-MR-00000"
        return super().create(vals_list)

    @api.depends(
        "input_ids.category",
        "input_ids.status_snapshot",
        "input_ids.numeric_value",
        "decision_ids",
        "action_ids.status",
    )
    def _compute_summary_counts(self):
        for review in self:
            inputs = review.input_ids
            review.objective_input_count = len(inputs.filtered(lambda item: item.category == "objectives"))
            review.kpi_input_count = len(inputs.filtered(lambda item: item.category == "kpi"))
            review.kpi_off_target_count = len(
                inputs.filtered(lambda item: item.category == "kpi" and item.status_snapshot == "off_target")
            )
            review.customer_issue_count = len(
                inputs.filtered(
                    lambda item: item.category in ("customer_performance", "customer_satisfaction")
                    and item.status_snapshot in ("issues", "off_target", "monitor")
                )
            )
            review.supplier_issue_count = len(
                inputs.filtered(
                    lambda item: item.category in ("supplier_performance", "supplier_evaluation")
                    and item.status_snapshot in ("monitor", "conditional", "disqualified", "issues")
                )
            )
            review.audits_reviewed_count = len(inputs.filtered(lambda item: item.category == "audit"))
            review.open_finding_count = len(
                inputs.filtered(
                    lambda item: item.category == "audit_findings"
                    and item.status_snapshot not in ("closed", "cancelled")
                )
            )
            review.high_risk_count = len(
                inputs.filtered(
                    lambda item: item.category == "risks"
                    and item.status_snapshot in ("high", "critical", "action_required", "monitoring")
                )
            )
            review.open_ncr_count = len(
                inputs.filtered(
                    lambda item: item.category == "ncr" and item.status_snapshot not in ("closed", "cancelled")
                )
            )
            review.open_capa_count = len(
                inputs.filtered(
                    lambda item: item.category == "capa"
                    and item.status_snapshot not in ("effective", "closed", "cancelled")
                )
            )
            review.previous_action_count = len(inputs.filtered(lambda item: item.category == "previous_actions"))
            review.decision_count = len(review.decision_ids)
            review.open_action_count = len(
                review.action_ids.filtered(lambda action: action.status not in ("completed", "verified", "cancelled"))
            )

    @api.constrains("period_start", "period_end", "planned_date", "actual_date", "next_review_date")
    def _check_dates(self):
        for review in self:
            if review.period_end < review.period_start:
                raise ValidationError("Management review period end cannot be before period start.")
            if review.planned_date and review.planned_date < review.period_start:
                raise ValidationError("Management review planned date cannot be before the reviewed period starts.")
            if review.actual_date and review.actual_date < review.period_start:
                raise ValidationError("Management review actual date cannot be before the reviewed period starts.")
            if review.actual_date and review.planned_date and review.actual_date < review.planned_date:
                raise ValidationError("Management review actual date cannot be before the planned date.")
            if review.next_review_date and review.actual_date and review.next_review_date <= review.actual_date:
                raise ValidationError("Next management review date must be after the actual review date.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage management reviews.")

    def _transition(self, state, decision, event_type="workflow", extra_values=None):
        self._check_manager_permission()
        allowed = {
            "preparing": ("draft",),
            "ready": ("preparing",),
            "in_progress": ("ready",),
            "completed": ("in_progress",),
            "cancelled": ("draft", "preparing", "ready", "in_progress"),
        }
        for review in self:
            if review.state not in allowed[state]:
                raise UserError(f"Management review cannot move from {review.state} to {state}.")
            previous = review.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            review.with_context(pm_qms_management_review_workflow=True).write(values)
            review._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user,
                approver=self.env.user if event_type == "closure" else None,
                decision=decision,
            )

    def action_prepare(self):
        self._transition("preparing", "Management review prepared")

    def action_generate_snapshot(self):
        self._check_manager_permission()
        for review in self:
            if review.state not in ("draft", "preparing"):
                raise UserError("Snapshots can only be generated while the review is draft or preparing.")
            snapshot_date = fields.Datetime.now()
            touched = set()
            changes = set()
            snapshot_review = review.with_context(
                pm_qms_snapshot_touched=touched,
                pm_qms_snapshot_changes=changes,
            )
            snapshot_review._generate_snapshot_inputs(snapshot_date)

            generated = review.with_context(active_test=False).input_ids.filtered(
                lambda item: item.is_system_generated
            )
            stale = generated.filtered(lambda item: item.id not in touched and item.active)
            if stale:
                stale.with_context(tracking_disable=True).write({"active": False})
                changes.add("stale")

            if changes:
                current = self.env["pm.qms.management.review.input"].browse(touched).exists()
                current.with_context(tracking_disable=True).write({"snapshot_date": snapshot_date})
                review.with_context(pm_qms_management_review_workflow=True).write(
                    {"snapshot_date": snapshot_date}
                )
                review._log_qms_event(
                    event_type="review",
                    previous_state=review.state,
                    new_state=review.state,
                    reviewer=self.env.user,
                    decision="Management review snapshot generated",
                )

    def action_mark_ready(self):
        for review in self:
            if not review.input_ids:
                raise UserError("Generate review inputs before marking the management review ready.")
        self._transition("ready", "Management review ready")

    def action_start_review(self):
        values = {}
        for review in self:
            if not review.actual_date:
                values[review.id] = {"actual_date": fields.Date.context_today(review)}
        for review in self:
            review._transition(
                "in_progress",
                "Management review started",
                extra_values=values.get(review.id),
            )

    def action_complete(self):
        for review in self:
            if not review.actual_date:
                raise UserError("Actual meeting date is required before completing the management review.")
            if not review.chair_id:
                raise UserError("Management review chair is required before completion.")
            if not review.participant_ids:
                raise UserError("At least one participant is required before completion.")
            if not review.input_ids:
                raise UserError("Generated review inputs are required before completion.")
            if not review.conclusion:
                raise UserError("Management conclusion is required before completion.")
            if not review.decision_ids and not review.action_ids:
                raise UserError("Record at least one management decision or action before completion.")
        self._transition(
            "completed",
            "Management review completed",
            event_type="closure",
            extra_values={"completed_date": fields.Datetime.now()},
        )

    def action_cancel(self):
        self._transition("cancelled", "Management review cancelled", event_type="closure")

    def _period_overlap_domain(self):
        self.ensure_one()
        return [("period_start", "<=", self.period_end), ("period_end", ">=", self.period_start)]

    def _create_input(self, category, title, source_type, **values):
        self.ensure_one()
        payload = {
            "review_id": self.id,
            "category": category,
            "title": title,
            "source_type": source_type,
            "snapshot_date": values.pop("snapshot_date", self.snapshot_date or fields.Datetime.now()),
            "period_start": values.pop("period_start", self.period_start),
            "period_end": values.pop("period_end", self.period_end),
            "is_system_generated": values.pop("is_system_generated", True),
        }
        payload.update(values)
        Input = self.env["pm.qms.management.review.input"]
        identity = [
            ("review_id", "=", self.id),
            ("category", "=", category),
            ("source_type", "=", source_type),
            ("is_system_generated", "=", True),
        ]
        if payload.get("source_identifier"):
            identity.append(("source_identifier", "=", payload["source_identifier"]))
        else:
            identity.append(("source_identifier", "=", False))
            identity.append(("title", "=", title))

        existing = Input.with_context(active_test=False).search(identity, order="id", limit=1)
        if not existing:
            record = Input.with_context(tracking_disable=True).create(payload)
            self.env.context.get("pm_qms_snapshot_changes", set()).add("create")
        else:
            writable = {
                name: value
                for name, value in payload.items()
                if name not in ("snapshot_date", "is_system_generated")
                and name in existing._fields
                and not existing._fields[name].readonly
                and not self._snapshot_value_equal(existing[name], existing._fields[name], value)
            }
            if existing.active is False:
                writable["active"] = True
            if writable:
                existing.with_context(tracking_disable=True).write(writable)
                self.env.context.get("pm_qms_snapshot_changes", set()).add("write")
            record = existing

        self.env.context.get("pm_qms_snapshot_touched", set()).add(record.id)
        return record

    @staticmethod
    def _snapshot_value_equal(current, field, incoming):
        if field.type == "many2one":
            incoming_id = incoming.id if hasattr(incoming, "id") else incoming
            return current.id == incoming_id
        return current == incoming

    def _generate_snapshot_inputs(self, snapshot_date):
        for review in self:
            review._snapshot_previous_actions(snapshot_date)
            review._snapshot_objectives(snapshot_date)
            review._snapshot_kpis(snapshot_date)
            review._snapshot_customer_performance(snapshot_date)
            review._snapshot_supplier_performance(snapshot_date)
            review._snapshot_audits(snapshot_date)
            review._snapshot_risks(snapshot_date)
            review._snapshot_ncr(snapshot_date)
            review._snapshot_capa(snapshot_date)

    def _base_domain(self):
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("organization_id", "=", self.organization_id.id),
        ]

    def _snapshot_previous_actions(self, snapshot_date):
        self.ensure_one()
        previous = self.search(
            [
                ("id", "!=", self.id),
                ("company_id", "=", self.company_id.id),
                ("organization_id", "=", self.organization_id.id),
                ("state", "=", "completed"),
                ("period_end", "<=", self.period_start),
            ],
            order="period_end desc, actual_date desc, id desc",
            limit=1,
        )
        for action in previous.action_ids:
            status = action.status
            if action.is_overdue and status not in ("completed", "verified", "cancelled"):
                status = "overdue"
            self._create_input(
                "previous_actions",
                action.name,
                "management_review_action",
                snapshot_date=snapshot_date,
                description=action.description,
                status_snapshot=status,
                text_value=(
                    f"Owner: {action.owner_id.display_name or 'Unassigned'}; "
                    f"due: {action.target_date or 'not set'}; "
                    f"completion: {action.completion_date or 'not completed'}"
                ),
                source_identifier=action.code,
            )

    def _snapshot_objectives(self, snapshot_date):
        self.ensure_one()
        Objective = self.env["pm.qms.objective"]
        domain = self._base_domain() + [
            ("date_start", "<=", self.period_end),
            ("target_date", ">=", self.period_start),
        ]
        for objective in Objective.search(domain, order="target_date, code"):
            self._create_input(
                "objectives",
                f"{objective.code} - {objective.name}",
                "objective",
                snapshot_date=snapshot_date,
                description=objective.description or objective.purpose,
                status_snapshot=objective.status,
                numeric_value=objective.target_value,
                target_snapshot=objective.target_value,
                unit_of_measure=objective.unit_of_measure,
                text_value=(
                    f"Owner: {objective.owner_id.display_name or 'Unassigned'}; "
                    f"target date: {objective.target_date}; status: {objective.status}"
                ),
                source_identifier=objective.code,
            )

    def _snapshot_kpis(self, snapshot_date):
        self.ensure_one()
        Measurement = self.env["pm.qms.kpi.measurement"]
        measurements = Measurement.search(
            self._base_domain()
            + [
                ("period_start", "<=", self.period_end),
                ("period_end", ">=", self.period_start),
                ("active", "=", True),
            ],
            order="kpi_id, period_end desc, measurement_date desc, id desc",
        )
        seen_kpis = set()
        for measurement in measurements:
            if measurement.kpi_id.id in seen_kpis:
                continue
            seen_kpis.add(measurement.kpi_id.id)
            kpi = measurement.kpi_id
            self._create_input(
                "kpi",
                f"{kpi.code} - {kpi.name}",
                "kpi_measurement",
                snapshot_date=snapshot_date,
                description=kpi.description or kpi.calculation_description,
                status_snapshot=measurement.status,
                numeric_value=measurement.value,
                target_snapshot=measurement.target_value_snapshot,
                unit_of_measure=kpi.unit_of_measure,
                period_start=measurement.period_start,
                period_end=measurement.period_end,
                text_value=(
                    f"Measurement date: {measurement.measurement_date}; "
                    f"trend: {kpi.trend_direction}; source: {measurement.source_type}"
                ),
                source_identifier=f"{kpi.code}:{measurement.period_start}:{measurement.period_end}",
            )

    def _snapshot_customer_performance(self, snapshot_date):
        self.ensure_one()
        Performance = self.env["pm.qms.customer.performance"]
        Satisfaction = self.env["pm.qms.customer.satisfaction"]
        for performance in Performance.search(self._base_domain() + self._period_overlap_domain()):
            status = "issues" if performance.complaint_count or performance.return_count or performance.rejection_count else "acceptable"
            self._create_input(
                "customer_performance",
                f"{performance.customer_id.display_name} customer performance",
                "customer_performance",
                snapshot_date=snapshot_date,
                status_snapshot=status,
                numeric_value=performance.customer_satisfaction_score,
                unit_of_measure="percent",
                period_start=performance.period_start,
                period_end=performance.period_end,
                text_value=(
                    f"Complaints: {performance.complaint_count}; open: {performance.open_complaint_count}; "
                    f"returns: {performance.return_count}; rejections: {performance.rejection_count}; "
                    f"delivery: {performance.delivery_performance}"
                ),
                source_identifier=f"customer-performance:{performance.id}",
            )
        for satisfaction in Satisfaction.search(self._base_domain() + self._period_overlap_domain()):
            status = "off_target" if satisfaction.score_percent < 80.0 else "on_target"
            self._create_input(
                "customer_satisfaction",
                f"{satisfaction.customer_id.display_name} satisfaction",
                "customer_satisfaction",
                snapshot_date=snapshot_date,
                status_snapshot=status,
                numeric_value=satisfaction.score_percent,
                unit_of_measure="percent",
                period_start=satisfaction.period_start,
                period_end=satisfaction.period_end,
                text_value=(
                    f"Method: {satisfaction.measurement_method}; score: {satisfaction.score}/"
                    f"{satisfaction.score_scale_max}; responses: {satisfaction.response_count}"
                ),
                source_identifier=f"customer-satisfaction:{satisfaction.id}",
            )

    def _snapshot_supplier_performance(self, snapshot_date):
        self.ensure_one()
        Performance = self.env["pm.qms.supplier.performance"]
        Evaluation = self.env["pm.qms.supplier.evaluation"]
        for performance in Performance.search(self._base_domain() + self._period_overlap_domain()):
            status = "monitor" if performance.overall_score < 80.0 or performance.supplier_ncr_count else "acceptable"
            self._create_input(
                "supplier_performance",
                f"{performance.supplier_id.display_name} supplier performance",
                "supplier_performance",
                snapshot_date=snapshot_date,
                status_snapshot=status,
                numeric_value=performance.overall_score,
                unit_of_measure="percent",
                period_start=performance.period_start,
                period_end=performance.period_end,
                text_value=(
                    f"Quality: {performance.quality_score}; delivery: {performance.delivery_score}; "
                    f"late deliveries: {performance.late_delivery_count}/{performance.total_delivery_count}; "
                    f"supplier NCR: {performance.supplier_ncr_count}"
                ),
                source_identifier=f"supplier-performance:{performance.id}",
            )
        for evaluation in Evaluation.search(self._base_domain() + self._period_overlap_domain()):
            self._create_input(
                "supplier_evaluation",
                f"{evaluation.supplier_id.display_name} supplier evaluation",
                "supplier_evaluation",
                snapshot_date=snapshot_date,
                status_snapshot=evaluation.status,
                numeric_value=evaluation.overall_score,
                unit_of_measure="percent",
                period_start=evaluation.period_start,
                period_end=evaluation.period_end,
                text_value=f"State: {evaluation.state}; evaluator: {evaluation.evaluator_id.display_name}",
                source_identifier=f"supplier-evaluation:{evaluation.id}",
            )

    def _snapshot_audits(self, snapshot_date):
        self.ensure_one()
        Audit = self.env["pm.qms.audit"]
        Finding = self.env["pm.qms.audit.finding"]
        audits = Audit.search(
            self._base_domain()
            + [
                "|",
                "&",
                ("actual_end", ">=", self.period_start),
                ("actual_end", "<=", self.period_end),
                "&",
                ("planned_end", ">=", self.period_start),
                ("planned_end", "<=", self.period_end),
            ],
            order="planned_end desc, code",
        )
        for audit in audits:
            self._create_input(
                "audit",
                f"{audit.code} - {audit.name}",
                "audit",
                snapshot_date=snapshot_date,
                description=audit.conclusion or audit.scope_summary,
                status_snapshot=audit.state,
                numeric_value=audit.total_finding_count,
                unit_of_measure="findings",
                period_start=audit.actual_start or audit.planned_start,
                period_end=audit.actual_end or audit.planned_end,
                text_value=(
                    f"Open findings: {audit.open_finding_count}; NCRs: {audit.ncr_count}; "
                    f"type: {audit.audit_type}"
                ),
                source_identifier=audit.code,
            )
        findings = Finding.search(
            self._base_domain() + [("state", "not in", ("closed", "cancelled"))],
            order="due_date, code",
        )
        for finding in findings:
            self._create_input(
                "audit_findings",
                f"{finding.code} - {finding.title}",
                "audit_finding",
                snapshot_date=snapshot_date,
                description=finding.description or finding.objective_evidence,
                status_snapshot=finding.state,
                numeric_value=finding.ncr_count,
                unit_of_measure="related NCRs",
                period_start=finding.audit_id.actual_start or finding.audit_id.planned_start,
                period_end=finding.audit_id.actual_end or finding.audit_id.planned_end,
                text_value=(
                    f"Classification: {finding.classification}; severity: {finding.severity or 'not used'}; "
                    f"due: {finding.due_date or 'not set'}"
                ),
                source_identifier=finding.code,
            )

    def _snapshot_risks(self, snapshot_date):
        self.ensure_one()
        Risk = self.env["pm.qms.risk"]
        records = Risk.search(
            self._base_domain()
            + [
                "|",
                ("state", "!=", "closed"),
                "&",
                ("review_date", ">=", self.period_start),
                ("review_date", "<=", self.period_end),
            ],
            order="risk_type, residual_score desc, target_date",
        )
        for risk in records:
            category = "opportunities" if risk.risk_type == "opportunity" else "risks"
            status = risk.residual_level if risk.risk_type == "risk" and risk.residual_level in ("high", "critical") else risk.state
            self._create_input(
                category,
                f"{risk.code} - {risk.name}",
                "risk",
                snapshot_date=snapshot_date,
                description=risk.description,
                status_snapshot=status,
                numeric_value=risk.residual_score,
                target_snapshot=risk.initial_score,
                unit_of_measure="score",
                text_value=(
                    f"Type: {risk.risk_type}; residual level: {risk.residual_level}; "
                    f"target date: {risk.target_date or 'not set'}; overdue: {risk.is_overdue}"
                ),
                source_identifier=risk.code,
            )

    def _snapshot_ncr(self, snapshot_date):
        self.ensure_one()
        Ncr = self.env["pm.qms.nonconformity"]
        ncrs = Ncr.search(
            self._base_domain()
            + [
                "|",
                ("state", "not in", ("closed", "cancelled")),
                "&",
                ("detected_date", ">=", self.period_start),
                ("detected_date", "<=", self.period_end),
            ],
            order="severity desc, target_date, code",
        )
        for ncr in ncrs:
            self._create_input(
                "ncr",
                f"{ncr.code} - {ncr.name}",
                "ncr",
                snapshot_date=snapshot_date,
                description=ncr.description,
                status_snapshot=ncr.state,
                numeric_value=ncr.days_overdue,
                unit_of_measure="days overdue",
                period_start=ncr.detected_date,
                period_end=ncr.closed_on.date() if ncr.closed_on else self.period_end,
                text_value=(
                    f"Source: {ncr.source_type}; severity: {ncr.severity}; "
                    f"target date: {ncr.target_date or 'not set'}; overdue: {ncr.is_overdue}"
                ),
                source_identifier=ncr.code,
            )

    def _snapshot_capa(self, snapshot_date):
        self.ensure_one()
        Capa = self.env["pm.qms.capa"]
        capas = Capa.search(
            self._base_domain()
            + [
                "|",
                ("state", "not in", ("effective", "closed", "cancelled")),
                "&",
                ("implementation_date", ">=", self.period_start),
                ("implementation_date", "<=", self.period_end),
            ],
            order="target_date, code",
        )
        for capa in capas:
            self._create_input(
                "capa",
                f"{capa.code} - {capa.name}",
                "capa",
                snapshot_date=snapshot_date,
                description=capa.problem_statement,
                status_snapshot=capa.state,
                numeric_value=capa.open_action_count,
                unit_of_measure="open actions",
                text_value=(
                    f"Source: {capa.source_type}; effectiveness result: {capa.effectiveness_result}; "
                    f"effectiveness due: {capa.effectiveness_review_date or 'not set'}; "
                    f"overdue: {capa.is_overdue or capa.effectiveness_is_overdue}"
                ),
                source_identifier=capa.code,
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_management_review_workflow"):
            raise AccessError("Use management review workflow actions to change status.")
        locked_fields = {
            "organization_id",
            "period_start",
            "period_end",
            "snapshot_date",
            "input_ids",
        }
        if locked_fields.intersection(vals) and any(review.state == "completed" for review in self):
            if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                raise AccessError("Only QMS Administrators can correct completed management review history.")
        return super().write(vals)

    def unlink(self):
        if any(review.state != "draft" for review in self):
            raise UserError("Only draft management reviews can be deleted.")
        return super().unlink()
