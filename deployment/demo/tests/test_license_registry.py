import base64
import hashlib
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


class DemoLicenseRegistryTests(unittest.TestCase):
    def test_demo_qa_v3_fingerprints_and_historical_coexistence(self):
        standard_path = REPO_ROOT / "addons/pm_qms_license/data/public_keys.json"
        demo_qa_path = REPO_ROOT / "deployment/demo/public_keys_demo_qa.json"
        standard_keys = json.loads(standard_path.read_text(encoding="utf-8"))["keys"]
        demo_qa_keys = json.loads(demo_qa_path.read_text(encoding="utf-8"))["keys"]

        self.assertEqual(
            set(demo_qa_keys),
            {
                "pmqms-demo-2026",
                "pmqms-license-2026",
                "pmqms-demo-2026-v2",
                "pmqms-demo-2026-v3",
            },
        )
        for historical_key_id, encoded_key in standard_keys.items():
            self.assertEqual(demo_qa_keys[historical_key_id], encoded_key)

        v3_public_raw = base64.b64decode(
            demo_qa_keys["pmqms-demo-2026-v3"], validate=True
        )
        self.assertEqual(len(v3_public_raw), 32)
        self.assertEqual(
            hashlib.sha256(v3_public_raw).hexdigest(),
            "2b9b1f747ffa21e0aed00e461f661ca81536689a842566263ac96948e65d6ee7",
        )
        v3_public_spki_der = bytes.fromhex("302a300506032b6570032100") + v3_public_raw
        self.assertEqual(
            hashlib.sha256(v3_public_spki_der).hexdigest(),
            "34263f9060419a073fcd32f1cc956d6535092dfd1f16cbea2b28a9cc4c0db083",
        )
        self.assertNotIn("pmqms-demo-2026-v3", standard_keys)


if __name__ == "__main__":
    unittest.main()
