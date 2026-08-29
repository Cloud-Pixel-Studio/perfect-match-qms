from pathlib import Path

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install", "qms_history")
class TestQmsHistoryCustomerUi(TransactionCase):
    def test_customer_history_assets_and_copy_are_scoped(self):
        addon_root = Path(__file__).parents[1]
        manifest = (addon_root / "__manifest__.py").read_text(encoding="utf-8")
        source = (addon_root / "static/src/js/qms_history.js").read_text(
            encoding="utf-8"
        )
        template = (addon_root / "static/src/xml/qms_history.xml").read_text(
            encoding="utf-8"
        )

        self.assertIn("pm_qms_app/static/src/js/qms_history.js", manifest)
        self.assertIn("pm_qms_app/static/src/xml/qms_history.xml", manifest)
        self.assertIn("pm_qms_app/static/src/scss/qms_history.scss", manifest)
        self.assertIn("o_pm_qms_customer_shell", source)
        self.assertIn("pm.qms.", source)
        self.assertIn("Perfect Match QMS · System", source)
        self.assertIn("QMS Activity &amp; History", template)
        self.assertIn("Internal Note", template)
        self.assertIn("<xpath expr=\"//button[hasclass('o-mail-Chatter-logNote')]\" position=\"replace\" mode=\"inner\">", template)
        self.assertNotIn("/text()", template)
        self.assertIn("Log note", template)
        self.assertIn('t-if">not isQmsCustomerHistory<', template)
        self.assertIn("o-mail-Chatter-sendMessage", template)
        self.assertIn("o-mail-Followers", template)
        self.assertNotIn('t-if">!isQmsCustomerHistory<', template)

    def test_customer_history_does_not_touch_global_odoo_messaging(self):
        addon_root = Path(__file__).parents[1]
        source = (addon_root / "static/src/js/qms_history.js").read_text(
            encoding="utf-8"
        )
        template = (addon_root / "static/src/xml/qms_history.xml").read_text(
            encoding="utf-8"
        )

        self.assertIn("threadModel", source)
        self.assertIn("mail.Chatter", template)
        self.assertNotIn("patch(MessagingMenu", source)
        self.assertNotIn("mail.message", template)

    def test_customer_history_scope_is_not_global(self):
        source = (Path(__file__).parents[1] / "static/src/js/qms_history.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("threadModel?.startsWith(PM_QMS_MODEL_PREFIX)", source)
        self.assertIn("document.documentElement.classList.contains", source)
