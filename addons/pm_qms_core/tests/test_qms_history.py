from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "qms_history")
class TestQmsHistory(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.quality_manager_group = cls.env.ref(
            "pm_qms_core.group_qms_quality_manager"
        )
        cls.viewer_group = cls.env.ref("pm_qms_core.group_qms_viewer")
        cls.manager = cls._create_user("history_manager", cls.quality_manager_group)
        cls.viewer = cls._create_user("history_viewer", cls.viewer_group)
        cls.technical = cls._create_user(
            "history_technical", cls.env.ref("base.group_system")
        )
        cls.organization = cls.env["pm.qms.organization"].create(
            {
                "name": "History Test Organization",
                "code": "PM-HISTORY-ORG",
                "company_id": cls.company.id,
            }
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "History Test Process",
                "code": "PM-HISTORY-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.risk = cls.env["pm.qms.risk"].create(
            {
                "name": "History protection fictional risk",
                "description": "Original test record for QMS history.",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "likelihood": 2,
                "impact": 2,
                "residual_likelihood": 2,
                "residual_impact": 2,
            }
        )

        cls.env.cr.precommit.data.pop("mail.tracking.pm.qms.risk", None)
    @classmethod
    def _create_user(cls, login, group):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, group.id])],
            }
        )

    def _flush_tracking(self):
        self.env.flush_all()
        self.risk.with_user(self.manager)._track_finalize()

    def _latest_tracking_message(self):
        return self.env["mail.message"].sudo().search(
            [
                ("model", "=", "pm.qms.risk"),
                ("res_id", "=", self.risk.id),
                ("tracking_value_ids", "!=", False),
            ],
            order="id desc",
            limit=1,
        )

    def test_human_tracking_preserves_author_and_values(self):
        self.risk.with_user(self.manager).write({"likelihood": 3})
        self._flush_tracking()

        message = self._latest_tracking_message()
        self.assertTrue(message)
        self.assertEqual(message.author_id, self.manager.partner_id)
        tracking = message.tracking_value_ids.sudo().filtered(
            lambda value: value.field_id.name == "likelihood"
        )
        self.assertEqual(len(tracking), 1)
        self.assertEqual(tracking.old_value_integer, 2)
        self.assertEqual(tracking.new_value_integer, 3)
        self.assertTrue(message.date)

    def test_system_actor_uses_stable_partner_identity(self):
        system_partner = self.env.ref("base.partner_root")
        self.assertTrue(system_partner.pm_qms_system_actor)
        self.assertFalse(self.manager.partner_id.pm_qms_system_actor)

    def test_customer_cannot_rewrite_or_delete_published_history(self):
        self.risk.with_user(self.manager).write({"likelihood": 4})
        self._flush_tracking()
        message = self._latest_tracking_message()
        tracking = message.tracking_value_ids.sudo()

        with self.assertRaises(AccessError):
            message.with_user(self.manager).write({"body": "changed"})
        with self.assertRaises(AccessError):
            message.with_user(self.manager).write(
                {"author_id": self.viewer.partner_id.id}
            )
        with self.assertRaises(AccessError):
            message.with_user(self.manager).unlink()
        with self.assertRaises(AccessError):
            tracking.with_user(self.manager).write({"old_value_integer": 99})
        with self.assertRaises(AccessError):
            tracking.with_user(self.manager).unlink()

    def test_internal_note_is_allowed_to_create_but_immutable_after_post(self):
        note = self.risk.with_user(self.manager).message_post(
            body="Original internal note for a fictional test record.",
            subtype_xmlid="mail.mt_note",
        )
        self.assertEqual(note.author_id, self.manager.partner_id)
        with self.assertRaises(AccessError):
            note.with_user(self.manager).write({"body": "rewritten"})
        with self.assertRaises(AccessError):
            note.with_user(self.manager).unlink()

    def test_technical_administrator_keeps_repair_exception(self):
        note = self.risk.with_user(self.manager).message_post(
            body="Technical repair test note.", subtype_xmlid="mail.mt_note"
        )
        technical_note = note.with_user(self.technical)
        technical_note._check_pm_qms_history_write({"body": "repair"})

    def test_viewer_can_read_but_cannot_post_or_mutate_history(self):
        note = self.risk.with_user(self.manager).message_post(
            body="Viewer-readable internal note.", subtype_xmlid="mail.mt_note"
        )
        self.assertTrue(note.with_user(self.viewer).read(["body"]))
        with self.assertRaises(AccessError):
            self.risk.with_user(self.viewer).message_post(
                body="Viewer must not create history.", subtype_xmlid="mail.mt_note"
            )
        with self.assertRaises(AccessError):
            note.with_user(self.viewer).write({"body": "Viewer mutation"})

    def test_non_pm_mail_message_is_not_restricted_by_pm_guard(self):
        partner = self.env["res.partner"].create({"name": "Native mail fixture"})
        message = partner.sudo().message_post(
            body="Unrelated native mail record fixture."
        )
        native_message = message.with_user(self.manager)
        self.assertFalse(native_message._pm_qms_history_protected())
        native_message.sudo().write({"body": "Edited native fixture."})
        self.assertIn("Edited native fixture.", str(native_message.body))
