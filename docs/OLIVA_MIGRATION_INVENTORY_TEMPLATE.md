# Oliva Migration Inventory Template

Use these columns for customer-authorized migration inventories. Do not add
external standard requirement text or unapproved customer data.

## Controlled Documents CSV

Required header:

```csv
document_code,title,revision,effective_date,owner_login,process_code,document_type,status,attachment_filename,attachment_base64,migration_note,control_instance_code
```

Allowed `status` values:

- `draft`
- `under_review`
- `approved`
- `active`
- `obsolete`

Notes:

- `document_code`, `title`, and `revision` are required.
- `effective_date` must use `YYYY-MM-DD` when provided.
- `owner_login` must match a user in the selected company or be blank.
- `process_code` must belong to the selected organization.
- `control_instance_code` must belong to the selected organization when used.
- `attachment_filename` must be a file name, not a path.
- `attachment_base64` must be base64 encoded.
- Only the current revision is imported. Historical revision reconstruction
  requires explicit customer-approved data and separate tooling.

Example row with placeholder content:

```csv
PILOT-DOC-001,PILOT VALIDATION - Controlled Document,A,2026-08-15,,OTUS-PM-QMS-DOC,procedure,active,pilot-document.txt,cGlsb3Q=,PILOT VALIDATION DATA - not production approval.,PM-QMS-INS-00001
```

## Evidence CSV

Required header:

```csv
evidence_name,control_instance_code,evidence_requirement_name,evidence_type,evidence_date,state,document_code,attachment_filename,attachment_base64,migration_note
```

Allowed `state` values:

- `draft`
- `submitted`
- `under_review`
- `rejected`

`accepted` is intentionally rejected by the import wizard. Evidence must be
accepted through QMS review workflow after import.

Notes:

- `evidence_name`, `control_instance_code`, and
  `evidence_requirement_name` are required.
- `evidence_requirement_name` must match an active requirement for the selected
  control instance's framework control.
- `document_code` must belong to the selected organization when used.
- `attachment_filename` must be a file name, not a path.
- `attachment_base64` must be base64 encoded.

Example row with placeholder content:

```csv
PILOT VALIDATION - Imported Evidence,PM-QMS-INS-00001,Approved current revision,approval,2026-08-15,under_review,PILOT-DOC-001,pilot-evidence.txt,cGlsb3Q=,PILOT VALIDATION DATA - requires review.
```
