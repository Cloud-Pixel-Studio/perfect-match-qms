import ast
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


SEED_PATH = Path(__file__).parents[1] / "seed_demo.py"
VALIDATE_PATH = Path(__file__).parents[1] / "validate_demo.py"
DEMO_PATH = Path(__file__).parents[1]
REPO_ROOT = Path(__file__).parents[3]


def load_guided_coverage_contract():
    tree = ast.parse(VALIDATE_PATH.read_text(encoding="utf-8"))
    names = {"GUIDED_EXCLUDED_MENU_IDS", "GUIDED_MODEL_EXAMPLES"}
    nodes = [node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign)) and any(
        isinstance(target, ast.Name) and target.id in names
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
    )]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(VALIDATE_PATH), "exec"), namespace)
    return namespace["GUIDED_EXCLUDED_MENU_IDS"], namespace["GUIDED_MODEL_EXAMPLES"]


GUIDED_EXCLUDED_MENU_IDS, GUIDED_MODEL_EXAMPLES = load_guided_coverage_contract()


def load_identity_helpers():
    tree = ast.parse(SEED_PATH.read_text(encoding="utf-8"))
    names = {
        "scoped_person_record_identity",
        "training_identity_domain",
        "qualification_identity_domain",
    }
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SEED_PATH), "exec"), namespace)
    return namespace


def load_capa_why_helper():
    tree = ast.parse(SEED_PATH.read_text(encoding="utf-8"))
    node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "upsert_capa_why")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SEED_PATH), "exec"), namespace)
    return namespace["upsert_capa_why"]


def load_seed_helpers(*names):
    tree = ast.parse(SEED_PATH.read_text(encoding="utf-8"))
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SEED_PATH), "exec"), namespace)
    return namespace


def load_seed_database_guard():
    tree = ast.parse(SEED_PATH.read_text(encoding="utf-8"))
    nodes = [
        item
        for item in tree.body
        if (
            isinstance(item, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "APPROVED_DEMO_DATABASES"
                for target in item.targets
            )
        )
        or (isinstance(item, ast.FunctionDef) and item.name == "validate_seed_database")
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SEED_PATH), "exec"), namespace)
    return namespace["validate_seed_database"]


def load_validation_database_guard():
    tree = ast.parse(VALIDATE_PATH.read_text(encoding="utf-8"))
    nodes = [
        item
        for item in tree.body
        if (
            isinstance(item, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "APPROVED_DEMO_DATABASES"
                for target in item.targets
            )
        )
        or (isinstance(item, ast.FunctionDef) and item.name == "validate_demo_database")
    ]
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(VALIDATE_PATH), "exec"), namespace)
    return namespace["validate_demo_database"]


def reconcile(rows, identity, values):
    matches = [
        row
        for row in rows
        if all(row.get(field) == value for field, _operator, value in identity)
    ]
    if matches:
        matches[0].update(values)
        return matches[0]
    row = {field: value for field, _operator, value in identity}
    row.update(values)
    row["id"] = max([item["id"] for item in rows] or [0]) + 1
    rows.append(row)
    return row


class SeedIdentityTests(unittest.TestCase):
    def setUp(self):
        self.helpers = load_identity_helpers()

    def test_seed_database_guard_accepts_original_demo_pair(self):
        guard = load_seed_database_guard()
        self.assertEqual(guard("demo", "pmqms_demo", "pmqms_demo"), "pmqms_demo")

    def test_seed_database_guard_accepts_demo2_only_for_demo2_instance(self):
        guard = load_seed_database_guard()
        self.assertEqual(guard("demo2", "pmqms_demo2", "pmqms_demo2"), "pmqms_demo2")
        with self.assertRaises(RuntimeError):
            guard("demo", "pmqms_demo2", "pmqms_demo2")

    def test_seed_database_guard_rejects_arbitrary_or_production_databases(self):
        guard = load_seed_database_guard()
        for instance, configured, actual in (
            ("demo2", "pmqms_production", "pmqms_production"),
            ("demo2", "production", "production"),
            ("production", "pmqms_production", "pmqms_production"),
        ):
            with self.subTest(instance=instance, database=actual):
                with self.assertRaises(RuntimeError):
                    guard(instance, configured, actual)

    def test_seed_database_guard_rejects_inconsistent_instance_and_database(self):
        guard = load_seed_database_guard()
        with self.assertRaises(RuntimeError):
            guard("demo2", "pmqms_demo2", "pmqms_demo")
        with self.assertRaises(RuntimeError):
            guard("demo2", "pmqms_demo", "pmqms_demo")

    def test_validation_guard_accepts_original_demo_database(self):
        guard = load_validation_database_guard()
        self.assertEqual(guard("demo", "pmqms_demo", "pmqms_demo"), "pmqms_demo")

    def test_validation_guard_accepts_demo2_database_for_demo2_instance(self):
        guard = load_validation_database_guard()
        self.assertEqual(guard("demo2", "pmqms_demo2", "pmqms_demo2"), "pmqms_demo2")

    def test_validation_guard_rejects_unauthorized_database(self):
        guard = load_validation_database_guard()
        with self.assertRaises(RuntimeError):
            guard("demo2", "pmqms_production", "pmqms_production")

    def test_validation_guard_rejects_inconsistent_instance_and_database(self):
        guard = load_validation_database_guard()
        with self.assertRaises(RuntimeError):
            guard("demo", "pmqms_demo2", "pmqms_demo2")
        with self.assertRaises(RuntimeError):
            guard("demo2", "pmqms_demo2", "pmqms_demo")

    def test_seed_launcher_passes_instance_and_keeps_demo2_paths_isolated(self):
        launcher = (SEED_PATH.parents[1] / "scripts" / "odoo-demo.sh").read_text(encoding="utf-8")
        seed_start = launcher.index("seed_demo() {")
        seed_end = launcher.index("\n}\n", seed_start)
        seed_block = launcher[seed_start:seed_end]
        self.assertIn('-e PMQMS_DEMO_INSTANCE="$PMQMS_DEMO_INSTANCE"', seed_block)
        self.assertIn('-e PMQMS_DEMO_DB="$DB_NAME"', seed_block)
        self.assertIn('DEFAULT_SECRETS_DIR="/opt/perfect-match/secrets/odoo-demo-isolated"', launcher)
        self.assertIn('DEFAULT_BACKUP_DIR="/opt/perfect-match/backups/odoo-demo-isolated"', launcher)
        self.assertIn('PMQMS_DEMO_INSTANCE" == demo2', launcher)
        self.assertIn('EXPECTED_DB_NAME="pmqms_${INSTANCE_SUFFIX}"', launcher)
        validate_start = launcher.index("validate_demo() {")
        validate_end = launcher.index("\n}\n", validate_start)
        validate_block = launcher[validate_start:validate_end]
        self.assertIn('-e PMQMS_DEMO_INSTANCE="$PMQMS_DEMO_INSTANCE"', validate_block)
        self.assertIn('-e PMQMS_DEMO_DB="$DB_NAME"', validate_block)

    def test_capa_why_helper_updates_only_answer_for_existing_slot(self):
        writes = []

        class Record:
            id = 7
            answer = "old answer"

            def write(self, values):
                writes.append(values)
                self.answer = values["answer"]
                return True

        record = Record()

        class Model:
            def search(self, domain, limit=1):
                self.domain = domain
                return record

        class Cursor:
            def savepoint(self):
                class Savepoint:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                return Savepoint()

        class Env:
            cr = Cursor()

            def __getitem__(self, key):
                self.model = Model()
                return self.model

        helper = load_capa_why_helper()
        env = Env()
        helper.__globals__["env"] = env
        capa = type("Capa", (), {"id": 42})()
        helper(capa, 1, "new answer")
        self.assertEqual(env.model.domain, [("capa_id", "=", 42), ("sequence", "=", 1)])
        self.assertEqual(writes, [{"answer": "new answer"}])

    def test_capa_why_helper_creates_missing_slot_with_initialization_context(self):
        class Model:
            def search(self, domain, limit=1):
                self.domain = domain
                return False

            def with_context(self, **context):
                self.context = context
                return self

            def create(self, values):
                self.values = values
                return values

        class Cursor:
            def savepoint(self):
                class Savepoint:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                return Savepoint()

        class Env:
            cr = Cursor()

            def __init__(self):
                self.model = Model()

            def __getitem__(self, key):
                return self.model

        helper = load_capa_why_helper()
        env = Env()
        helper.__globals__["env"] = env
        capa = type("Capa", (), {"id": 42})()
        helper(capa, 1, "new answer")
        self.assertEqual(env.model.context, {"pm_qms_capa_initialize": True})
        self.assertEqual(env.model.values, {"capa_id": 42, "sequence": 1, "answer": "new answer"})

    def test_capa_why_helper_does_not_write_when_answer_is_unchanged(self):
        writes = []

        class Record:
            id = 7
            answer = "same answer"

            def write(self, values):
                writes.append(values)

        class Model:
            def search(self, domain, limit=1):
                return Record()

        class Cursor:
            def savepoint(self):
                class Savepoint:
                    def __enter__(self):
                        return self

                    def __exit__(self, *args):
                        return False

                return Savepoint()

        class Env:
            cr = Cursor()

            def __getitem__(self, key):
                return Model()

        helper = load_capa_why_helper()
        helper.__globals__["env"] = Env()
        helper.__globals__["warnings"] = []
        helper(type("Capa", (), {"id": 42})(), 1, "same answer")
        self.assertEqual(writes, [])

    def test_training_identity_excludes_due_date(self):
        identity = self.helpers["training_identity_domain"](7, 11, 2, 1)
        self.assertEqual(
            identity,
            [
                ("person_id", "=", 7),
                ("course_id", "=", 11),
                ("organization_id", "=", 2),
                ("company_id", "=", 1),
            ],
        )
        self.assertNotIn("due_date", {field for field, _, _ in identity})

    def test_qualification_identity_excludes_expiration_date(self):
        identity = self.helpers["qualification_identity_domain"](7, 12, 2, 1)
        self.assertIn(("qualification_type_id", "=", 12), identity)
        self.assertNotIn("expiration_date", {field for field, _, _ in identity})

    def test_training_cross_day_preserves_id_and_updates_date(self):
        rows = []
        identity = self.helpers["training_identity_domain"](7, 11, 2, 1)
        first = reconcile(rows, identity, {"due_date": "2026-08-29"})
        second = reconcile(rows, identity, {"due_date": "2026-08-30"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(rows, [{**{field: value for field, _, value in identity}, "due_date": "2026-08-30", "id": 1}])

    def test_qualification_cross_day_preserves_id_and_updates_expiration(self):
        rows = []
        identity = self.helpers["qualification_identity_domain"](7, 12, 2, 1)
        first = reconcile(rows, identity, {"expiration_date": "2026-08-29"})
        second = reconcile(rows, identity, {"expiration_date": "2026-09-05"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["expiration_date"], "2026-09-05")

    def test_identity_is_scoped_by_organization_and_company(self):
        identity = self.helpers["training_identity_domain"](7, 11, 2, 1)
        other_scope = self.helpers["training_identity_domain"](7, 11, 3, 1)
        self.assertNotEqual(identity, other_scope)

    def test_seed_calls_use_stable_domains(self):
        tree = ast.parse(SEED_PATH.read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "upsert"
        ]
        target_models = {
            "pm.qms.training.record": "training_identity_domain",
            "pm.qms.qualification.record": "qualification_identity_domain",
        }
        for model_name, helper_name in target_models.items():
            call = next(node for node in calls if node.args[0].value == model_name)
            extra = next(keyword.value for keyword in call.keywords if keyword.arg == "extra_domain")
            self.assertIsInstance(extra, ast.Call)
            self.assertEqual(extra.func.id, helper_name)

    def test_capa_why_seed_uses_dedicated_fixed_slot_helper(self):
        tree = ast.parse(SEED_PATH.read_text(encoding="utf-8"))
        helper = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "upsert_capa_why"
        )
        source = ast.unparse(helper)
        self.assertIn("env['pm.qms.capa.why']", source)
        self.assertIn("[('capa_id', '=', capa.id), ('sequence', '=', sequence)]", source)
        self.assertIn("record.write({'answer': answer})", source)
        self.assertIn('with_context(pm_qms_capa_initialize=True)', source)
        self.assertIn("'capa_id': capa.id", source)
        self.assertIn("'sequence': sequence", source)
        self.assertIn("'answer': answer", source)
        self.assertNotIn("upsert(\"pm.qms.capa.why\"", SEED_PATH.read_text(encoding="utf-8"))

    def test_capa_why_helper_contract_is_executable(self):
        namespace = load_seed_helpers("upsert_capa_why")
        source = ast.unparse(next(node for node in ast.parse(SEED_PATH.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef) and node.name == "upsert_capa_why"))
        self.assertEqual(set(namespace) - {"__builtins__"}, {"upsert_capa_why"})
        self.assertNotIn("question", source)
        self.assertNotIn("organization_id", source)
        self.assertNotIn("company_id", source)

    def test_cost_events_use_quality_manager_and_fail_loudly(self):
        source = SEED_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        event_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "ensure_cost_event"
        ]
        self.assertEqual({call.args[0].value for call in event_calls}, {"APEX-CQ-001", "APEX-CQ-002"})
        self.assertEqual(sum(len(call.args[4].elts) for call in event_calls), 6)
        self.assertIn("event.with_user(demo_user).action_confirm()", source)
        self.assertIn("raise RuntimeError(f\"Cost event confirmation failed for {code}: {exc}\")", source)
        self.assertNotIn("warnings.append(f\"cost_confirm:", source)

    def test_demo_validation_uses_quality_manager_for_action_center(self):
        source = VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn('EXPECTED_QMS_PERSONAS["Quality Manager"]', source)
        self.assertNotIn('EXPECTED_ADMIN_LOGIN)], limit=1)', source)
        self.assertIn('require(len(values) >= 8, "expected source-driven Action Center values")', source)
        self.assertIn('require(len(source_types) >= 6, "expected multiple Action Center source types")', source)

    def test_demo_validation_requires_confirmed_cost_event_and_six_lines(self):
        source = VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn('event.state == "confirmed"', source)
        self.assertIn('expected_cost_lines = {"APEX-CQ-001": 4, "APEX-CQ-002": 2}', source)
        self.assertIn('require(confirmed_events == 2, "expected both canonical Cost of Quality events confirmed")', source)
        self.assertIn('require(line_count == expected_lines, f"expected {expected_lines} lines for {code}, found {line_count}")', source)
        self.assertIn('require(lines >= 6, "expected six Cost of Quality lines")', source)

    def test_generic_upsert_skips_unchanged_values(self):
        namespace = load_seed_helpers("upsert", "field_value_equal")
        writes = []

        class Field:
            readonly = False
            type = "char"

        class Record:
            def __getitem__(self, key):
                return "same value"

            def write(self, values):
                writes.append(values)

        class Model:
            _fields = {"name": Field()}

            def search(self, domain, limit=1):
                return Record()

            def browse(self):
                return None

        class Savepoint:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        class Cursor:
            def savepoint(self):
                return Savepoint()

        class Env:
            cr = Cursor()

            def __getitem__(self, key):
                return Model()

        namespace["model_exists"] = lambda _model_name: True
        namespace["domain_for"] = lambda _model_name, **_kwargs: [("name", "=", "demo")]
        namespace["filtered"] = lambda _model_name, vals: dict(vals)
        namespace["env"] = Env()
        namespace["warnings"] = []

        namespace["upsert"]("demo.model", name="same value")

        self.assertEqual(writes, [])

    def test_many2many_commands_follow_odoo_semantics(self):
        namespace = load_seed_helpers("field_value_equal")
        equal = namespace["field_value_equal"]

        class Field:
            type = "many2many"

        class Relation:
            def __init__(self, ids):
                self.ids = ids

        field = Field()

        def assert_equal(current_ids, commands, expected):
            self.assertEqual(equal(Relation(current_ids), field, commands), expected)

        assert_equal({1, 2}, [(4, 1, 0)], True)
        assert_equal({1}, [(4, 2, 0)], False)
        assert_equal({1, 2}, [(6, 0, [1, 2])], True)
        assert_equal({1, 2}, [(6, 0, [1])], False)
        assert_equal({1, 2}, [(3, 2, 0)], False)
        assert_equal({1, 2}, [(3, 9, 0)], True)
        assert_equal(set(), [(5, 0, 0)], True)
        assert_equal({1}, [(5, 0, 0)], False)
        assert_equal({1}, [(0, 0, {})], False)
        assert_equal({1}, [(1, 1, {})], False)
        assert_equal({1}, [(99, 1, 0)], False)
        assert_equal({1, 2}, [(5, 0, 0), (4, 2, 0), (4, 1, 0)], True)
        assert_equal({1}, [(2, 1, 0)], False)

    def test_generic_upsert_only_writes_missing_many2many_links(self):
        namespace = load_seed_helpers("upsert", "field_value_equal")

        class Field:
            readonly = False
            type = "many2many"

        class Relation:
            def __init__(self, ids):
                self.ids = ids

        def run(current_ids, commands):
            writes = []

            class Record:
                def __getitem__(self, key):
                    return Relation(set(current_ids))

                def write(self, values):
                    writes.append(values)

            class Model:
                _fields = {"company_ids": Field()}

                def search(self, domain, limit=1):
                    return Record()

                def browse(self):
                    return None

            class Savepoint:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

            class Cursor:
                def savepoint(self):
                    return Savepoint()

            class Env:
                cr = Cursor()

                def __getitem__(self, key):
                    return Model()

            namespace["model_exists"] = lambda _model_name: True
            namespace["domain_for"] = lambda _model_name, **_kwargs: [("id", "=", 1)]
            namespace["filtered"] = lambda _model_name, vals: dict(vals)
            namespace["env"] = Env()
            namespace["warnings"] = []
            namespace["upsert"]("demo.model", vals={"company_ids": commands})
            return writes

        self.assertEqual(run({1, 2}, [(4, 1, 0)]), [])
        self.assertEqual(run({1}, [(4, 2, 0)]), [{"company_ids": [(4, 2, 0)]}])

    def test_existing_persona_password_is_not_rewritten(self):
        seed = Path(__file__).parents[1] / "seed_demo.py"
        source = seed.read_text(encoding="utf-8")
        existing_user_block = source[source.index('if user:'):source.index('users[role] = user')]
        self.assertNotIn('writable = {k: v for k, v in vals.items() if k != "login" and "password"', existing_user_block)
        self.assertIn('if persona_password:', existing_user_block)
        self.assertIn('vals["password"] = persona_password', existing_user_block)

    def test_existing_technical_admin_password_is_not_rewritten(self):
        seed = Path(__file__).parents[1] / "seed_demo.py"
        source = seed.read_text(encoding="utf-8")
        admin_block = source[source.index('technical_admin_values = {'):source.index('framework_organization =')]
        self.assertNotIn('technical_admin_values["password"] = ADMIN_PASSWORD\nif technical_admin:', admin_block)
        self.assertIn('if technical_admin:', admin_block)
        self.assertIn('if ADMIN_PASSWORD:', admin_block)
        self.assertIn('technical_admin_values["password"] = ADMIN_PASSWORD', admin_block)

    def test_validator_has_canonical_process_and_duplicate_gates(self):
        source = VALIDATE_PATH.read_text(encoding="utf-8")
        for code in (
            "APEX-LEAD", "APEX-QMS", "APEX-CUST", "APEX-SUP", "APEX-REC",
            "APEX-PROD", "APEX-FIN", "APEX-SHIP", "APEX-DOC", "APEX-AUD",
            "APEX-TRN", "APEX-CAL",
        ):
            self.assertIn(code, source)
        self.assertIn("duplicate canonical Demo training records detected", source)
        self.assertIn("duplicate canonical Demo qualification records detected", source)


class GuidedCoverageContractTests(unittest.TestCase):
    def test_every_functional_window_menu_has_a_fixture_and_matrix_row(self):
        actions = {}
        menu_models = {}
        for xml_path in (REPO_ROOT / "addons").glob("pm_qms_*/**/*.xml"):
            try:
                tree = ET.parse(xml_path)
            except ET.ParseError:
                continue
            for record in tree.findall(".//record"):
                if record.get("model") != "ir.actions.act_window":
                    continue
                res_model = record.find("field[@name='res_model']")
                if record.get("id") and res_model is not None:
                    actions[record.get("id")] = res_model.text or ""
        for xml_path in (REPO_ROOT / "addons").glob("pm_qms_*/**/*.xml"):
            try:
                tree = ET.parse(xml_path)
            except ET.ParseError:
                continue
            for menu in tree.findall(".//menuitem"):
                if not menu.get("action"):
                    continue
                menu_id = menu.get("id")
                action_id = menu.get("action").split(".")[-1]
                if menu_id and action_id in actions:
                    menu_models[menu_id] = actions[action_id]

        functional_menus = set(menu_models) - GUIDED_EXCLUDED_MENU_IDS
        self.assertTrue(functional_menus)
        self.assertFalse(GUIDED_EXCLUDED_MENU_IDS - set(menu_models))
        self.assertEqual(set(menu_models.values()) - {menu_models[item] for item in GUIDED_EXCLUDED_MENU_IDS}, set(GUIDED_MODEL_EXAMPLES))
        matrix = (DEMO_PATH / "DEMO_COVERAGE_MATRIX.md").read_text(encoding="utf-8")
        missing_rows = sorted(menu_id for menu_id in functional_menus if f"`{menu_id}`" not in matrix)
        self.assertEqual(missing_rows, [])

    def test_guided_examples_are_explained_with_state_and_relationships(self):
        matrix = (DEMO_PATH / "DEMO_COVERAGE_MATRIX.md").read_text(encoding="utf-8")
        for required in ("Quality Manager", "Quality Supervisor", "Document Controller", "Internal Auditor", "Process Owner", "Management User", "QMS Viewer", "state", "Relationships", "APEX-CQ-001", "APEX-CQ-002"):
            with self.subTest(required=required):
                self.assertIn(required, matrix)
        for model_name, anchor in GUIDED_MODEL_EXAMPLES.items():
            with self.subTest(model=model_name):
                self.assertIn(model_name, matrix)
                self.assertIn(anchor.split()[0].lower(), matrix.lower())

    def test_capa_state_variants_use_official_workflow_actions(self):
        source = SEED_PATH.read_text(encoding="utf-8")
        for action_name in (
            "action_start_analysis",
            "action_plan_actions",
            "action_start_implementation",
            "action_complete_implementation",
            "action_mark_effective",
            "action_close",
        ):
            self.assertIn(f".{action_name}()", source)
        self.assertIn('code="APEX-CAPA-003"', source)
        self.assertNotIn('"state": "closed"', source)

    def test_validator_checks_full_menu_example_and_site_scope_visibility(self):
        source = VALIDATE_PATH.read_text(encoding="utf-8")
        self.assertIn("for model_name, fixture_anchor in GUIDED_MODEL_EXAMPLES.items()", source)
        self.assertIn("visible_site_ids <= effective_site_ids", source)
        self.assertIn('"pm.qms.equipment"', source)

    def test_management_user_read_only_contract_has_positive_and_negative_qms_coverage(self):
        capa_tests = (REPO_ROOT / "addons/pm_qms_capa/tests/test_capa.py").read_text(encoding="utf-8")
        risk_tests = (REPO_ROOT / "addons/pm_qms_risk/tests/test_risk.py").read_text(encoding="utf-8")
        for test_name in (
            "test_management_user_is_read_only_for_capa",
            "test_management_user_is_read_only_for_all_capa_child_models",
        ):
            self.assertIn(f"def {test_name}(", capa_tests)
        self.assertIn("self.assertEqual(model.with_user(management).browse(record.id).id, record.id)", capa_tests)
        self.assertIn("self.assertTrue(model.with_user(management).search_count", capa_tests)
        self.assertIn("action.with_user(management).action_start()", capa_tests)
        self.assertIn("action.with_user(management).action_complete()", capa_tests)
        self.assertGreaterEqual(capa_tests.count("with self.assertRaises(AccessError):"), 4)
        self.assertIn("test_management_user_is_read_only", risk_tests)
        self.assertIn("action_start_monitoring", risk_tests)
        self.assertIn('with self.assertRaises(AccessError):\n            self.env["pm.qms.risk"].with_user(management).create', risk_tests)
        self.assertIn('with self.assertRaises(AccessError):\n            risk.with_user(management).write', risk_tests)
        self.assertIn('with self.assertRaises(AccessError):\n            risk.with_user(management).unlink()', risk_tests)


if __name__ == "__main__":
    unittest.main()
