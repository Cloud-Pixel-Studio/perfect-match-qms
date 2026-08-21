from odoo import api, fields, models


class PmQmsDashboard(models.TransientModel):
    _name = "pm.qms.dashboard"
    _description = "Perfect Match QMS Dashboard"

    organization_id = fields.Many2one(
        "pm.qms.organization",
        string="Organization",
        default=lambda self: self._default_organization(),
        required=True,
    )
    implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        string="Implementation",
        default=lambda self: self._default_implementation_project(),
    )
    organization_count = fields.Integer(compute="_compute_dashboard")
    has_multiple_organizations = fields.Boolean(compute="_compute_dashboard")
    dashboard_timestamp = fields.Datetime(string="Dashboard Refreshed", compute="_compute_dashboard")

    readiness_percent = fields.Float(compute="_compute_dashboard", digits=(16, 2))
    total_controls = fields.Integer(compute="_compute_dashboard")
    ready_controls = fields.Integer(compute="_compute_dashboard")
    partial_controls = fields.Integer(compute="_compute_dashboard")
    gap_controls = fields.Integer(compute="_compute_dashboard")
    not_applicable_controls = fields.Integer(compute="_compute_dashboard")

    total_activities = fields.Integer(compute="_compute_dashboard")
    completed_activities = fields.Integer(compute="_compute_dashboard")
    open_activities = fields.Integer(compute="_compute_dashboard")
    overdue_activities = fields.Integer(compute="_compute_dashboard")

    required_evidence = fields.Integer(compute="_compute_dashboard")
    accepted_evidence = fields.Integer(compute="_compute_dashboard")
    missing_evidence = fields.Integer(compute="_compute_dashboard")
    pending_review_evidence = fields.Integer(compute="_compute_dashboard")

    open_risks = fields.Integer(compute="_compute_dashboard")
    high_open_risks = fields.Integer(compute="_compute_dashboard")
    open_ncr = fields.Integer(compute="_compute_dashboard")
    overdue_ncr = fields.Integer(compute="_compute_dashboard")
    open_capa = fields.Integer(compute="_compute_dashboard")
    overdue_capa = fields.Integer(compute="_compute_dashboard")
    open_audit_findings = fields.Integer(compute="_compute_dashboard")
    overdue_audit_findings = fields.Integer(compute="_compute_dashboard")

    active_objectives = fields.Integer(compute="_compute_dashboard")
    objectives_on_target = fields.Integer(compute="_compute_dashboard")
    active_kpis = fields.Integer(compute="_compute_dashboard")
    kpis_on_target = fields.Integer(compute="_compute_dashboard")
    customer_performance_issues = fields.Integer(compute="_compute_dashboard")
    supplier_performance_issues = fields.Integer(compute="_compute_dashboard")

    last_management_review_id = fields.Many2one("pm.qms.management.review", compute="_compute_dashboard")
    last_management_review_date = fields.Date(compute="_compute_dashboard")
    open_management_review_actions = fields.Integer(compute="_compute_dashboard")

    attention_overdue_activities = fields.Integer(compute="_compute_dashboard")
    attention_missing_evidence = fields.Integer(compute="_compute_dashboard")
    attention_high_risks = fields.Integer(compute="_compute_dashboard")
    attention_overdue_capa = fields.Integer(compute="_compute_dashboard")
    attention_open_findings = fields.Integer(compute="_compute_dashboard")

    next_action_1_name = fields.Char(compute="_compute_dashboard")
    next_action_1_reason = fields.Char(compute="_compute_dashboard")
    next_action_2_name = fields.Char(compute="_compute_dashboard")
    next_action_2_reason = fields.Char(compute="_compute_dashboard")
    next_action_3_name = fields.Char(compute="_compute_dashboard")
    next_action_3_reason = fields.Char(compute="_compute_dashboard")

    def _organization_domain(self):
        return [("company_id", "in", self.env.companies.ids)]

    def _default_organization(self):
        if self.env.context.get("active_model") == "pm.qms.organization" and self.env.context.get("active_id"):
            organization = self.env["pm.qms.organization"].browse(self.env.context["active_id"]).exists()
            if organization:
                return organization.id
        return self.env["pm.qms.organization"].search(self._organization_domain(), limit=1, order="code, name, id").id

    def _latest_project_for_organization(self, organization):
        if not organization:
            return self.env["pm.qms.implementation.project"]
        return self.env["pm.qms.implementation.project"].search(
            [
                ("organization_id", "=", organization.id),
                ("company_id", "=", organization.company_id.id),
                ("state", "!=", "cancelled"),
            ],
            limit=1,
            order="write_date desc, id desc",
        )

    def _default_implementation_project(self):
        organization = self.env["pm.qms.organization"].browse(self._default_organization()).exists()
        return self._latest_project_for_organization(organization).id

    @api.onchange("organization_id")
    def _onchange_organization_id(self):
        self.implementation_project_id = self._latest_project_for_organization(self.organization_id)

    @api.onchange("implementation_project_id")
    def _onchange_implementation_project_id(self):
        if self.implementation_project_id:
            self.organization_id = self.implementation_project_id.organization_id

    def _base_domain(self):
        self.ensure_one()
        if not self.organization_id:
            return [("id", "=", 0)]
        return [
            ("company_id", "=", self.organization_id.company_id.id),
            ("organization_id", "=", self.organization_id.id),
        ]

    def _project_controls(self):
        self.ensure_one()
        if not self.implementation_project_id:
            return self.env["pm.qms.implementation.control"]
        return self.implementation_project_id.implementation_control_ids.filtered("active")

    def _set_zero_metrics(self):
        for name in self._metric_fields():
            self[name] = 0
        self.readiness_percent = 0.0
        self.last_management_review_id = False
        self.last_management_review_date = False
        self.next_action_1_name = False
        self.next_action_1_reason = False
        self.next_action_2_name = False
        self.next_action_2_reason = False
        self.next_action_3_name = False
        self.next_action_3_reason = False

    @api.model
    def _metric_fields(self):
        return [
            "organization_count",
            "total_controls",
            "ready_controls",
            "partial_controls",
            "gap_controls",
            "not_applicable_controls",
            "total_activities",
            "completed_activities",
            "open_activities",
            "overdue_activities",
            "required_evidence",
            "accepted_evidence",
            "missing_evidence",
            "pending_review_evidence",
            "open_risks",
            "high_open_risks",
            "open_ncr",
            "overdue_ncr",
            "open_capa",
            "overdue_capa",
            "open_audit_findings",
            "overdue_audit_findings",
            "active_objectives",
            "objectives_on_target",
            "active_kpis",
            "kpis_on_target",
            "customer_performance_issues",
            "supplier_performance_issues",
            "open_management_review_actions",
            "attention_overdue_activities",
            "attention_missing_evidence",
            "attention_high_risks",
            "attention_overdue_capa",
            "attention_open_findings",
        ]

    @api.depends("organization_id", "implementation_project_id")
    def _compute_dashboard(self):
        now = fields.Datetime.now()
        organization_count = self.env["pm.qms.organization"].search_count(self._organization_domain())
        for dashboard in self:
            dashboard._set_zero_metrics()
            dashboard.organization_count = organization_count
            dashboard.has_multiple_organizations = organization_count > 1
            dashboard.dashboard_timestamp = now
            if not dashboard.organization_id:
                continue

            if dashboard.implementation_project_id and dashboard.implementation_project_id.organization_id != dashboard.organization_id:
                dashboard.implementation_project_id = dashboard._latest_project_for_organization(dashboard.organization_id)

            controls = dashboard._project_controls()
            project = dashboard.implementation_project_id
            if project:
                dashboard.readiness_percent = project.readiness_percent
                dashboard.total_controls = project.total_controls
                dashboard.ready_controls = project.ready_controls
                dashboard.partial_controls = project.partial_controls
                dashboard.gap_controls = project.gap_controls
                dashboard.not_applicable_controls = project.not_applicable_controls
                dashboard.total_activities = project.total_generated_tasks
                dashboard.completed_activities = project.completed_tasks
                dashboard.open_activities = project.open_tasks
                dashboard.overdue_activities = project.overdue_tasks
                dashboard.required_evidence = project.required_evidence
                dashboard.accepted_evidence = project.accepted_evidence
                dashboard.missing_evidence = project.missing_evidence
                dashboard.pending_review_evidence = sum(controls.mapped("evidence_under_review_count"))
                for index, next_action in enumerate(project._recommended_next_action_values(limit=3), start=1):
                    dashboard[f"next_action_{index}_name"] = next_action.get("name")
                    dashboard[f"next_action_{index}_reason"] = next_action.get("reason")

            base_domain = dashboard._base_domain()
            Risk = dashboard.env["pm.qms.risk"]
            Ncr = dashboard.env["pm.qms.nonconformity"]
            Capa = dashboard.env["pm.qms.capa"]
            Finding = dashboard.env["pm.qms.audit.finding"]
            Objective = dashboard.env["pm.qms.objective"]
            Kpi = dashboard.env["pm.qms.kpi"]
            CustomerPerformance = dashboard.env["pm.qms.customer.performance"]
            SupplierPerformance = dashboard.env["pm.qms.supplier.performance"]
            Review = dashboard.env["pm.qms.management.review"]
            ReviewAction = dashboard.env["pm.qms.management.review.action"]

            open_risk_domain = base_domain + [("state", "!=", "closed")]
            dashboard.open_risks = Risk.search_count(open_risk_domain)
            dashboard.high_open_risks = Risk.search_count(open_risk_domain + [("residual_level", "in", ("high", "critical"))])

            open_ncr_domain = base_domain + [("state", "not in", ("closed", "cancelled"))]
            dashboard.open_ncr = Ncr.search_count(open_ncr_domain)
            dashboard.overdue_ncr = Ncr.search_count(open_ncr_domain + [("is_overdue", "=", True)])

            open_capa_domain = base_domain + [("state", "not in", ("effective", "closed", "cancelled"))]
            dashboard.open_capa = Capa.search_count(open_capa_domain)
            dashboard.overdue_capa = Capa.search_count(
                open_capa_domain + ["|", ("is_overdue", "=", True), ("effectiveness_is_overdue", "=", True)]
            )

            open_finding_domain = base_domain + [("state", "not in", ("closed", "cancelled"))]
            dashboard.open_audit_findings = Finding.search_count(open_finding_domain)
            dashboard.overdue_audit_findings = Finding.search_count(
                open_finding_domain + ["|", ("is_overdue", "=", True), ("follow_up_is_overdue", "=", True)]
            )

            active_objective_domain = base_domain + [("status", "in", ("active", "achieved", "not_achieved"))]
            dashboard.active_objectives = Objective.search_count(active_objective_domain)
            dashboard.objectives_on_target = Objective.search_count(base_domain + [("status", "=", "achieved")])

            active_kpi_domain = base_domain + [("status", "=", "active")]
            dashboard.active_kpis = Kpi.search_count(active_kpi_domain)
            dashboard.kpis_on_target = Kpi.search_count(active_kpi_domain + [("latest_status", "=", "on_target")])

            customer_records = CustomerPerformance.search(base_domain)
            dashboard.customer_performance_issues = len(
                customer_records.filtered(
                    lambda item: bool(item.open_complaint_count or item.return_count or item.rejection_count)
                )
            )
            supplier_records = SupplierPerformance.search(base_domain)
            dashboard.supplier_performance_issues = len(
                supplier_records.filtered(lambda item: item.overall_score < 80.0 or bool(item.supplier_ncr_count))
            )

            last_review = Review.search(base_domain + [("state", "=", "completed")], order="actual_date desc, period_end desc, id desc", limit=1)
            dashboard.last_management_review_id = last_review
            dashboard.last_management_review_date = last_review.actual_date or last_review.period_end
            dashboard.open_management_review_actions = ReviewAction.search_count(
                base_domain + [("status", "not in", ("completed", "verified", "cancelled"))]
            )

            dashboard.attention_overdue_activities = dashboard.overdue_activities
            dashboard.attention_missing_evidence = dashboard.missing_evidence
            dashboard.attention_high_risks = dashboard.high_open_risks
            dashboard.attention_overdue_capa = dashboard.overdue_capa
            dashboard.attention_open_findings = dashboard.open_audit_findings

    def _action_for_xmlid(self, xmlid, domain=None, context=None, name=None):
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        if domain is not None:
            action["domain"] = domain
        if context is not None:
            action["context"] = context
        if name:
            action["name"] = name
        return action

    def _selected_implementation_domain(self):
        self.ensure_one()
        if self.implementation_project_id:
            return [("implementation_project_id", "=", self.implementation_project_id.id)]
        return [("organization_id", "=", self.organization_id.id)] if self.organization_id else [("id", "=", 0)]

    def action_continue_implementation(self):
        self.ensure_one()
        action = self._action_for_xmlid("pm_qms_implementation.action_pm_qms_implementation_project")
        if self.implementation_project_id:
            action.update({"res_id": self.implementation_project_id.id, "views": [(False, "form")], "view_mode": "form"})
        elif self.organization_id:
            action["domain"] = [("organization_id", "=", self.organization_id.id)]
        return action

    def action_review_gaps(self):
        self.ensure_one()
        domain = self._selected_implementation_domain() + [("readiness_state", "in", ("gap", "partial"))]
        return self._action_for_xmlid("pm_qms_implementation.action_pm_qms_implementation_control", domain=domain, name="Readiness Gaps")

    def action_review_evidence(self):
        self.ensure_one()
        domain = self._base_domain() + [("state", "in", ("draft", "submitted", "under_review", "rejected", "expired"))]
        if self.implementation_project_id:
            instance_ids = self.implementation_project_id.implementation_control_ids.mapped("control_instance_id").ids
            domain = [("control_instance_id", "in", instance_ids), ("state", "in", ("draft", "submitted", "under_review", "rejected", "expired"))]
        return self._action_for_xmlid("pm_qms_evidence.action_pm_qms_evidence", domain=domain, name="Evidence Requiring Attention")

    def action_run_readiness_assessment(self):
        self.ensure_one()
        if self.implementation_project_id:
            return self.implementation_project_id.action_open_readiness_center()
        domain = [("organization_id", "=", self.organization_id.id)] if self.organization_id else [("id", "=", 0)]
        return self._action_for_xmlid("pm_qms_implementation.action_pm_qms_readiness_assessment", domain=domain)

    def action_view_risks(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_risk.action_pm_qms_risk",
            domain=self._base_domain() + [("state", "!=", "closed")],
            name="Open Risks & Opportunities",
        )

    def action_view_nonconformities(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_ncr.action_pm_qms_nonconformity",
            domain=self._base_domain() + [("state", "not in", ("closed", "cancelled"))],
            name="Open Nonconformities",
        )

    def action_view_capa(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_capa.action_pm_qms_capa",
            domain=self._base_domain() + [("state", "not in", ("effective", "closed", "cancelled"))],
            name="Open CAPA",
        )

    def action_view_audit_findings(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_audit.action_pm_qms_audit_finding",
            domain=self._base_domain() + [("state", "not in", ("closed", "cancelled"))],
            name="Open Audit Findings",
        )

    def action_view_objectives(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_kpi.action_pm_qms_objective",
            domain=self._base_domain(),
            name="Quality Objectives",
        )

    def action_view_kpis(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_kpi.action_pm_qms_kpi",
            domain=self._base_domain(),
            name="KPIs",
        )

    def action_view_management_reviews(self):
        self.ensure_one()
        return self._action_for_xmlid(
            "pm_qms_management_review.action_pm_qms_management_review",
            domain=self._base_domain(),
            name="Management Reviews",
        )
