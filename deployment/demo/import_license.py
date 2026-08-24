from pathlib import Path
import json


license_path = Path("/run/pmqms-demo-license.pmql")
if not license_path.exists():
    raise RuntimeError("Demo license mount is missing.")
document = json.loads(license_path.read_text(encoding="utf-8"))
payload = document.get("payload", {})
current = env["pm.qms.license"].sudo().search([("is_current", "=", True)], limit=1)
if current and current.license_id == payload.get("license_id") and current.license_revision == payload.get("license_revision") and current.signature == document.get("signature"):
    license_record = current
    print("DEMO_LICENSE_ALREADY_CURRENT")
else:
    license_record = env["pm.qms.license"].import_document(license_path.read_bytes())
env.cr.commit()
print("DEMO_LICENSE_IMPORTED")
print(f"license_id={license_record.license_id}")
print(f"license_revision={license_record.license_revision}")
print(f"state={license_record.state}")
print(f"environment={license_record.environment_short}")
