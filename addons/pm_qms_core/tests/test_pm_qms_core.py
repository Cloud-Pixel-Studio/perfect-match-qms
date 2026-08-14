from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsCore(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Supplier Management",
                "code": "PM-PROC-SUP",
                "description": "Perfect Match proprietary process definition.",
            }
        )

    def test_control_sequence_and_state_flow(self):
        control = self.env["pm.qms.control"].create(
            {
                "name": "Supplier Qualification and Monitoring",
                "objective": "Define and monitor supplier qualification using Perfect Match methodology.",
                "process_id": self.process.id,
            }
        )

        self.assertTrue(control.code.startswith("PM-QMS-CTRL-"))
        self.assertEqual(control.state, "draft")

        control.action_activate()
        self.assertEqual(control.state, "active")

        control.action_retire()
        self.assertEqual(control.state, "retired")

    def test_external_mapping_is_separate_from_proprietary_control(self):
        control = self.env["pm.qms.control"].create(
            {
                "name": "Evidence Review",
                "objective": "Define evidence review expectations using proprietary Perfect Match wording.",
                "process_id": self.process.id,
            }
        )
        mapping = self.env["pm.qms.external.mapping"].create(
            {
                "control_id": control.id,
                "framework": "iso9001",
                "reference": "8.4",
                "notes": "Reference identifier only.",
            }
        )

        self.assertEqual(mapping.control_id, control)
        self.assertFalse(hasattr(mapping, "standard_text"))
        self.assertFalse(hasattr(control, "standard_text"))

    def test_activity_and_evidence_requirements(self):
        control = self.env["pm.qms.control"].create(
            {
                "name": "Process Evidence Planning",
                "objective": "Define activities and evidence requirements for QMS implementation.",
                "process_id": self.process.id,
            }
        )

        activity = self.env["pm.qms.implementation.activity"].create(
            {
                "control_id": control.id,
                "name": "Review current process ownership",
            }
        )
        evidence = self.env["pm.qms.evidence.requirement"].create(
            {
                "control_id": control.id,
                "name": "Approved process owner record",
                "evidence_type": "record",
            }
        )

        self.assertEqual(activity.company_id, control.company_id)
        self.assertEqual(evidence.company_id, control.company_id)
        self.assertTrue(evidence.required)
