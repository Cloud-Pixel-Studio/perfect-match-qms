from pathlib import Path


license_path = Path("/run/pmqms-demo-license.pmql")
if not license_path.exists():
    raise RuntimeError("Demo license mount is missing.")
license_record = env["pm.qms.license"].import_document(license_path.read_bytes())
env.cr.commit()
print("DEMO_LICENSE_IMPORTED")
print(f"license_id={license_record.license_id}")
print(f"license_revision={license_record.license_revision}")
print(f"state={license_record.state}")
print(f"environment={license_record.environment_short}")
