from pathlib import Path
import re
import xml.etree.ElementTree as ET

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
        self.assertIn("<xpath expr=\"//button[hasclass('o-mail-Chatter-logNote')]\" position=\"replace\">", template)
        self.assertNotIn("/text()", template)
        self.assertIn('class=\"o-mail-Chatter-logNote btn text-nowrap me-1\"', template)
        self.assertIn("state.composerType === 'note'", template)
        self.assertIn("state.composerType !== 'note'", template)
        self.assertIn('t-att-disabled=\"!state.thread.canPostMessage and props.threadId\"', template)
        self.assertIn('data-hotkey=\"shift+m\"', template)
        self.assertIn('t-on-click=\"() => this.toggleComposer(\'note\')\"', template)
        self.assertIn("Log note", template)
        self.assertIn('t-if">!isQmsCustomerHistory<', template)
        self.assertNotIn('t-if">not isQmsCustomerHistory<', template)
        self.assertIn("o-mail-Chatter-sendMessage", template)
        self.assertIn("o-mail-Followers", template)

        root = ET.fromstring(template)
        scoped_conditions = {}
        for xpath_node in root.findall(".//xpath"):
            expr = xpath_node.attrib.get("expr", "")
            if "o-mail-Chatter-sendMessage" in expr or "o-mail-Followers" in expr:
                attribute = next(
                    (
                        node
                        for node in xpath_node.findall("attribute")
                        if node.attrib.get("name") == "t-if"
                    ),
                    None,
                )
                scoped_conditions[expr] = attribute.text if attribute is not None else None

        self.assertEqual(
            scoped_conditions.get("//button[hasclass('o-mail-Chatter-sendMessage')]"),
            "!isQmsCustomerHistory",
        )
        self.assertEqual(
            scoped_conditions.get("//div[hasclass('o-mail-Followers')]"),
            "!isQmsCustomerHistory",
        )
        self.assertEqual(
            list(scoped_conditions.values()).count("!isQmsCustomerHistory"),
            2,
        )

    def test_customer_frontend_xml_rejects_python_style_boolean_not(self):
        xml_root = Path(__file__).parents[1] / "static/src/xml"
        invalid_expressions = []
        for path in sorted(xml_root.rglob("*.xml")):
            source = path.read_text(encoding="utf-8")
            invalid_expressions.extend(
                (path.name, match.group(0))
                for match in re.finditer(
                    r"(?:t-(?:if|elif)\s*=\s*[\"']\s*not\b|>\s*not\s+isQms\w*)",
                    source,
                )
            )

        self.assertEqual(
            invalid_expressions,
            [],
            "Python-style boolean expressions must not enter Owl frontend XML",
        )

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
