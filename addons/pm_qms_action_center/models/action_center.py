from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class PmQmsActionCenterLine(models.TransientModel):
    _name = "pm.qms.action.center.line"
    _description = "Perfect Match QMS Action Center Line"
    _order = "due_bucket_sequence, due_date, normalized_priority desc, source_code, id"

    source_key = fields.Char(required=True, readonly=True, index=True)
    source_model = fields.Char(required=True, readonly=True, index=True)
    source_id = fields.Integer(required=True, readonly=True, index=True)
    action_kind = fields.Char(required=True, readonly=True, index=True)
    source_module = fields.Char(readonly=True)
    category = fields.Selection(
        [
            ("implementation", "Implementation"),
            ("risk", "Risk & Improvement"),
            ("audit", "Audit"),
            ("people", "People & Competency"),
            ("calibration", "Equipment & Calibration"),
            ("customer", "Customer Quality"),
            ("supplier", "Supplier Quality"),
            ("management_review", "Management Review"),
        ],
        readonly=True,
    )
    source_code = fields.Char(readonly=True)
    title = fields.Char(readonly=True)
    description = fields.Text(readonly=True)
    owner_user_id = fields.Many2one("res.users", readonly=True)
    person_id = fields.Many2one("pm.qms.person", readonly=True)
    organization_id = fields.Many2one("pm.qms.organization", readonly=True, index=True)
    company_id = fields.Many2one("res.company", readonly=True, index=True)
    process_id = fields.Many2one("pm.qms.process", readonly=True)
    due_date = fields.Date(readonly=True, index=True)
    due_bucket = fields.Selection(
        [
            ("overdue", "Overdue"),
            ("today", "Due Today"),
            ("soon", "Due Soon"),
            ("open", "Open / No Due Date"),
        ],
        readonly=True,
        index=True,
    )
    due_bucket_sequence = fields.Integer(readonly=True, index=True)
    days_overdue = fields.Integer(readonly=True)
    source_state = fields.Char(readonly=True)
    source_state_label = fields.Char(readonly=True)
    normalized_priority = fields.Selection(
        [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")],
        readonly=True,
        default="normal",
    )
    is_overdue = fields.Boolean(readonly=True, index=True)

    @api.model
    def action_open_center(self):
        self._refresh_for_current_user()
        return {
            "type": "ir.actions.act_window",
            "name": "Unified Action Center",
            "res_model": self._name,
            "view_mode": "list,form,pivot,graph",
            "domain": [("create_uid", "=", self.env.user.id)],
            "context": {"search_default_open": 1},
        }

    def action_refresh(self):
        return self.action_open_center()

    def action_open_source(self):
        self.ensure_one()
        spec = self._provider_by_key().get((self.source_model, self.action_kind))
        if not spec:
            raise UserError("This action source is not registered for opening.")
        if self.source_model not in self.env:
            raise UserError("This action source model is not installed.")
        record = self.env[self.source_model].browse(self.source_id).exists()
        if not record:
            raise UserError("The source record no longer exists.")
        record.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": self.title or record.display_name,
            "res_model": self.source_model,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _refresh_for_current_user(self):
        self.search([("create_uid", "=", self.env.user.id)]).with_context(pm_qms_action_center_refresh=True).unlink()
        values = self._collect_action_values()
        if values:
            self.create(values)
        return len(values)

    @api.model
    def _collect_action_values(self, organization=False):
        values = []
        for spec in self._provider_specs():
            if spec["model"] not in self.env:
                continue
            model = self.env[spec["model"]]
            domain = list(spec["domain"])
            if organization and "organization_id" in model._fields:
                domain.append(("organization_id", "=", organization.id))
            for record in model.search(domain, order=spec.get("order") or "id"):
                if not self._record_matches_provider(record, spec):
                    continue
                line_values = self._line_values_from_record(record, spec)
                if line_values:
                    values.append(line_values)
        return values

    @api.model
    def _record_matches_provider(self, record, spec):
        if spec["model"] == "pm.qms.equipment":
            return record.calibration_status in ("due", "due_soon", "overdue")
        return True

    @api.model
    def _line_values_from_record(self, record, spec):
        due_date = self._field_value(record, spec.get("due_field"))
        today = fields.Date.context_today(self)
        days_overdue = (today - due_date).days if due_date and due_date < today else 0
        bucket, sequence = self._due_bucket(due_date)
        state = self._field_value(record, spec.get("state_field"))
        state_label = self._selection_label(record, spec.get("state_field"), state)
        owner = self._field_value(record, spec.get("owner_field"))
        person = self._field_value(record, spec.get("person_field"))
        if person:
            try:
                person.check_access("read")
            except AccessError:
                # A source record can be in the user's organization while its
                # assigned person belongs to another site scope. Do not leak
                # that person through a derived action-center row.
                return False
        if not owner and person and "user_id" in person._fields:
            owner = person.user_id
        return {
            "source_key": f"{record._name}:{record.id}:{spec['action_kind']}",
            "source_model": record._name,
            "source_id": record.id,
            "action_kind": spec["action_kind"],
            "source_module": spec["module"],
            "category": spec["category"],
            "source_code": self._display_text(record, spec.get("code_field")),
            "title": self._display_text(record, spec.get("title_field")) or record.display_name,
            "description": self._display_text(record, spec.get("description_field")),
            "owner_user_id": owner.id if owner else False,
            "person_id": person.id if person else False,
            "organization_id": self._field_id(record, "organization_id"),
            "company_id": self._field_id(record, "company_id"),
            "process_id": self._field_id(record, "process_id"),
            "due_date": due_date,
            "due_bucket": bucket,
            "due_bucket_sequence": sequence,
            "days_overdue": days_overdue,
            "source_state": state,
            "source_state_label": state_label or state,
            "normalized_priority": self._normalize_priority(record, spec),
            "is_overdue": bool(days_overdue),
        }

    @api.model
    def _due_bucket(self, due_date):
        today = fields.Date.context_today(self)
        if due_date and due_date < today:
            return "overdue", 10
        if due_date and due_date == today:
            return "today", 20
        if due_date and (due_date - today).days <= self._due_soon_days():
            return "soon", 30
        return "open", 40

    @api.model
    def _due_soon_days(self):
        value = self.env["ir.config_parameter"].sudo().get_param("pm_qms.action_center.due_soon_days", "7")
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 7

    @api.model
    def _field_value(self, record, field_name):
        return record[field_name] if field_name and field_name in record._fields else False

    @api.model
    def _field_id(self, record, field_name):
        value = self._field_value(record, field_name)
        return value.id if value else False

    @api.model
    def _display_text(self, record, field_name):
        value = self._field_value(record, field_name)
        return value.display_name if hasattr(value, "display_name") else value

    @api.model
    def _selection_label(self, record, field_name, value):
        if not field_name or not value or field_name not in record._fields:
            return False
        selection = record._fields[field_name].selection
        if callable(selection):
            selection = selection(record)
        return dict(selection or []).get(value, value)

    @api.model
    def _normalize_priority(self, record, spec):
        field_name = spec.get("priority_field")
        value = self._field_value(record, field_name) if field_name else False
        if value in ("urgent", "critical"):
            return "urgent"
        if value in ("high", "major"):
            return "high"
        if value in ("low", "minor"):
            return "low"
        if bool(self._field_value(record, spec.get("overdue_field"))):
            return "high"
        return "normal"

    @api.model
    def _provider_by_key(self):
        return {(spec["model"], spec["action_kind"]): spec for spec in self._provider_specs()}

    @api.model
    def _provider_specs(self):
        return [
            self._spec("pm.qms.nonconformity", "ncr_closure", "pm_qms_ncr", "risk", [("state", "not in", ("closed", "cancelled"))], "owner_id", "target_date", "state", "is_overdue", "severity", "code", "name", "description"),
            self._spec("pm.qms.risk", "risk_response", "pm_qms_risk", "risk", [("state", "not in", ("closed",))], "owner_id", "target_date", "state", "is_overdue", "risk_level", "code", "name", "description"),
            self._spec("pm.qms.audit.finding", "finding_follow_up", "pm_qms_audit", "audit", [("state", "not in", ("closed", "cancelled"))], "owner_id", "due_date", "state", "is_overdue", "severity", "code", "title", "description"),
            self._spec("pm.qms.capa", "capa_due", "pm_qms_capa", "risk", [("state", "not in", ("effective", "closed", "cancelled"))], "action_owner_id", "target_date", "state", "is_overdue", False, "code", "name", "problem_statement"),
            self._spec("pm.qms.capa", "effectiveness_review", "pm_qms_capa", "risk", [("effectiveness_required", "=", True), ("state", "not in", ("effective", "closed", "cancelled"))], "owner_id", "effectiveness_review_date", "state", "effectiveness_is_overdue", False, "code", "name", "effectiveness_notes"),
            self._spec("pm.qms.capa.action", "capa_action", "pm_qms_capa", "risk", [("status", "not in", ("completed", "verified", "cancelled"))], "owner_id", "target_date", "status", "is_overdue", False, "name", "name", "description"),
            self._spec("pm.qms.management.review.action", "management_review_action", "pm_qms_management_review", "management_review", [("status", "not in", ("completed", "verified", "cancelled"))], "owner_id", "target_date", "status", "is_overdue", False, "code", "name", "description"),
            self._spec("pm.qms.training.record", "training_completion", "pm_qms_people", "people", [("state", "in", ("planned", "overdue"))], False, "due_date", "state", False, False, "course_id", "course_id", "notes", person_field="person_id"),
            self._spec("pm.qms.qualification.record", "qualification_expiration", "pm_qms_people", "people", [("status", "in", ("expiring", "expired"))], False, "expiration_date", "status", False, False, "qualification_type_id", "qualification_type_id", "notes", person_field="person_id"),
            self._spec("pm.qms.document.acknowledgment", "document_acknowledgment", "pm_qms_people", "people", [("state", "=", "pending")], False, "due_date", "state", "is_overdue", False, "revision_id", "revision_id", False, person_field="person_id"),
            self._spec("pm.qms.equipment", "calibration_due", "pm_qms_calibration", "calibration", [("calibration_required", "=", True), ("lifecycle_state", "not in", ("retired",))], False, "next_due_date", "calibration_status", False, False, "code", "name", "calibration_notes", person_field="responsible_person_id"),
            self._spec("pm.qms.calibration.impact.assessment", "oot_impact_assessment", "pm_qms_calibration", "calibration", [("state", "not in", ("closed", "cancelled"))], False, False, "state", False, "risk_level", "code", "name", "impact_summary", person_field="assessor_person_id"),
            self._spec("pm.qms.customer.complaint", "customer_response", "pm_qms_customer_quality", "customer", [("state", "not in", ("closed", "cancelled"))], "response_owner_id", "response_due_date", "state", "is_response_overdue", "priority", "code", "name", "description"),
            self._spec("pm.qms.customer.complaint", "containment", "pm_qms_customer_quality", "customer", [("containment_required", "=", True), ("containment_status", "not in", ("complete", "not_required")), ("state", "not in", ("closed", "cancelled"))], "containment_owner_id", "containment_due_date", "state", False, "priority", "code", "name", "containment_action"),
            self._spec("pm.qms.quality.alert", "quality_alert_review", "pm_qms_customer_quality", "customer", [("state", "in", ("draft", "published"))], "owner_id", "review_date", "state", False, "severity", "code", "name", "message"),
            self._spec("pm.qms.eight.d", "eight_d_due", "pm_qms_customer_quality", "customer", [("state", "not in", ("closed", "cancelled"))], "owner_id", "due_date", "state", "is_overdue", False, "code", "name", "problem_statement"),
            self._spec("pm.qms.supplier.issue", "supplier_issue", "pm_qms_customer_quality", "supplier", [("state", "not in", ("closed", "cancelled"))], "owner_id", "containment_due_date", "state", False, "severity", "code", "name", "description"),
            self._spec("pm.qms.scar", "scar_response", "pm_qms_customer_quality", "supplier", [("state", "not in", ("closed", "cancelled"))], "owner_id", "response_due_date", "state", "is_overdue", "severity", "code", "name", "problem_statement"),
        ]

    @api.model
    def _spec(self, model, action_kind, module, category, domain, owner_field, due_field, state_field, overdue_field, priority_field, code_field, title_field, description_field, person_field=False):
        return {
            "model": model,
            "action_kind": action_kind,
            "module": module,
            "category": category,
            "domain": domain,
            "owner_field": owner_field,
            "person_field": person_field,
            "due_field": due_field,
            "state_field": state_field,
            "overdue_field": overdue_field,
            "priority_field": priority_field,
            "code_field": code_field,
            "title_field": title_field,
            "description_field": description_field,
        }

    def write(self, vals):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Action Center lines are refreshed from source records and cannot be edited.")
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("pm_qms_action_center_refresh") and not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Action Center lines are refreshed from source records and cannot be deleted manually.")
        return super().unlink()
