from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsCalibrationImpactAssessment(models.Model):
    _name = "pm.qms.calibration.impact.assessment"
    _description = "Perfect Match QMS Out-of-Tolerance Impact Assessment"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    equipment_id = fields.Many2one("pm.qms.equipment", required=True, ondelete="restrict", index=True, tracking=True)
    event_id = fields.Many2one("pm.qms.calibration.event", required=True, ondelete="restrict", index=True)
    organization_id = fields.Many2one(related="equipment_id.organization_id", store=True, readonly=True, index=True)
    company_id = fields.Many2one(related="equipment_id.company_id", store=True, readonly=True, index=True)
    process_id = fields.Many2one(related="equipment_id.process_id", store=True, readonly=True)
    assessor_person_id = fields.Many2one("pm.qms.person", string="Assessor", ondelete="restrict")
    assessment_date = fields.Date(default=fields.Date.context_today)
    last_acceptable_event_id = fields.Many2one("pm.qms.calibration.event", readonly=True)
    exposure_start = fields.Date(readonly=True)
    exposure_end = fields.Date()
    used_during_exposure = fields.Selection(
        [("no", "No"), ("yes", "Yes"), ("unknown", "Unknown")],
        default="unknown",
        required=True,
        tracking=True,
    )
    impact_conclusion = fields.Selection(
        [
            ("no_impact", "No Impact"),
            ("potential_impact", "Potential Impact"),
            ("confirmed_impact", "Confirmed Impact"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        required=True,
        tracking=True,
    )
    reviewed_scope = fields.Text()
    containment_action = fields.Text()
    evaluation_summary = fields.Text()
    disposition = fields.Text()
    affected_reference_ids = fields.One2many(
        "pm.qms.calibration.affected.reference",
        "assessment_id",
        string="Affected References",
    )
    ncr_required = fields.Boolean(default=True)
    ncr_id = fields.Many2one("pm.qms.nonconformity", ondelete="restrict")
    capa_required = fields.Boolean(default=False)
    capa_id = fields.Many2one("pm.qms.capa", ondelete="restrict")
    approved_by_id = fields.Many2one("res.users", readonly=True)
    approval_date = fields.Date(readonly=True)
    closure_date = fields.Date(readonly=True)
    notes = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("disposition", "Disposition"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Impact assessment code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.calibration.impact") or "PM-OOT-00000"
        return super().create(vals_list)

    @api.constrains("equipment_id", "event_id", "assessor_person_id", "ncr_id", "capa_id", "exposure_start", "exposure_end")
    def _check_alignment(self):
        for assessment in self:
            if assessment.event_id.equipment_id != assessment.equipment_id:
                raise ValidationError("Impact assessment event must belong to the selected equipment.")
            if assessment.assessor_person_id and assessment.assessor_person_id.company_id != assessment.company_id:
                raise ValidationError("Assessor must belong to the same company.")
            if assessment.ncr_id and (
                assessment.ncr_id.company_id != assessment.company_id
                or assessment.ncr_id.organization_id != assessment.organization_id
            ):
                raise ValidationError("Linked NCR must match the assessment company and organization.")
            if assessment.capa_id and (
                assessment.capa_id.company_id != assessment.company_id
                or assessment.capa_id.organization_id != assessment.organization_id
            ):
                raise ValidationError("Linked CAPA must match the assessment company and organization.")
            if assessment.exposure_start and assessment.exposure_end and assessment.exposure_end < assessment.exposure_start:
                raise ValidationError("Potential exposure end cannot be before exposure start.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage OOT impact assessments.")

    def _transition(self, state, decision, event_type="workflow", values=None):
        self._check_manager_permission()
        previous = {record.id: record.state for record in self}
        payload = {"state": state}
        if values:
            payload.update(values)
        self.with_context(pm_qms_calibration_impact_workflow=True).write(payload)
        for record in self:
            record._log_qms_event(event_type, previous[record.id], state, reviewer=self.env.user, decision=decision)

    def action_start_review(self):
        self._transition("in_review", "OOT impact assessment review started")

    def action_set_disposition(self):
        for assessment in self:
            if not assessment.evaluation_summary:
                raise UserError("Evaluation summary is required before disposition.")
        self._transition("disposition", "OOT impact assessment disposition set", event_type="review")

    def action_create_ncr(self):
        self.ensure_one()
        self._check_manager_permission()
        if self.ncr_id:
            return self._open_record(self.ncr_id, "pm_qms_ncr.action_pm_qms_nonconformity")
        if not self.process_id:
            raise UserError("Assign a QMS process to the equipment before creating an NCR.")
        ncr = self.env["pm.qms.nonconformity"].create(
            {
                "name": f"OOT impact assessment for {self.equipment_id.code}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "process",
                "description": self.evaluation_summary or self.event_id.as_found_condition or self.event_id.notes or "Out-of-tolerance equipment impact assessment.",
                "severity": "major" if self.impact_conclusion in ("potential_impact", "confirmed_impact", "unknown") else "minor",
                "containment_required": True,
                "containment_action": self.containment_action,
                "related_evidence_ids": [(6, 0, self.event_id.related_evidence_ids.ids)],
                "attachment_ids": [(4, self.event_id.certificate_attachment_id.id)] if self.event_id.certificate_attachment_id else [],
                "calibration_event_id": self.event_id.id,
                "calibration_impact_assessment_id": self.id,
            }
        )
        self.write({"ncr_id": ncr.id, "ncr_required": True})
        return self._open_record(ncr, "pm_qms_ncr.action_pm_qms_nonconformity")

    def action_link_capa_from_ncr(self):
        self.ensure_one()
        self._check_manager_permission()
        if self.capa_id:
            return self._open_record(self.capa_id, "pm_qms_capa.action_pm_qms_capa")
        if not self.ncr_id:
            raise UserError("Create or link an NCR before deriving CAPA from the impact assessment.")
        action = self.ncr_id.action_create_capa()
        capa = self.env["pm.qms.capa"].browse(action.get("res_id")).exists()
        if capa:
            capa.write(
                {
                    "calibration_event_id": self.event_id.id,
                    "calibration_impact_assessment_id": self.id,
                    "attachment_ids": [(4, self.event_id.certificate_attachment_id.id)] if self.event_id.certificate_attachment_id else [],
                }
            )
            self.write({"capa_id": capa.id, "capa_required": True})
        return action

    def action_close(self):
        for assessment in self:
            if assessment.impact_conclusion == "unknown":
                raise UserError("Impact conclusion must be determined before closing.")
            if not assessment.disposition:
                raise UserError("Disposition is required before closing.")
            if assessment.ncr_required and not assessment.ncr_id:
                raise UserError("Create or link the required NCR before closing.")
            if assessment.capa_required and not assessment.capa_id:
                raise UserError("Create or link the required CAPA before closing.")
        self._transition(
            "closed",
            "OOT impact assessment closed",
            event_type="closure",
            values={
                "approved_by_id": self.env.user.id,
                "approval_date": fields.Date.context_today(self),
                "closure_date": fields.Date.context_today(self),
            },
        )

    def action_cancel(self):
        self._transition("cancelled", "OOT impact assessment cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_calibration_impact_workflow"):
            raise AccessError("Use impact-assessment workflow actions to change status.")
        return super().write(vals)

    def _open_record(self, record, xmlid):
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        action.update({"res_id": record.id, "views": [(False, "form")], "view_mode": "form"})
        return action


class PmQmsCalibrationAffectedReference(models.Model):
    _name = "pm.qms.calibration.affected.reference"
    _description = "Perfect Match QMS Calibration Affected Reference"
    _order = "assessment_id, reference_date, name"

    assessment_id = fields.Many2one("pm.qms.calibration.impact.assessment", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="assessment_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="assessment_id.organization_id", store=True, readonly=True, index=True)
    name = fields.Char(required=True)
    reference_date = fields.Date()
    description = fields.Text()
    impact_notes = fields.Text()
    disposition = fields.Selection(
        [
            ("no_impact", "No Impact"),
            ("potential_impact", "Potential Impact"),
            ("confirmed_impact", "Confirmed Impact"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        required=True,
    )
