import ast
import unittest
from pathlib import Path


SEED_PATH = Path(__file__).parents[1] / "seed_demo.py"
VALIDATE_PATH = Path(__file__).parents[1] / "validate_demo.py"


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


if __name__ == "__main__":
    unittest.main()
