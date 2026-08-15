# Perfect Match QMS Migration Tools

`pm_qms_migration` provides controlled import helpers for customer onboarding
and pilot migrations.

The addon is reusable product infrastructure. It does not contain Oliva Torras
data, customer documents, attachments, or external standard text.

## Scope

- Controlled document metadata and current-revision import.
- Optional uploaded attachment content through CSV base64 fields.
- Evidence metadata import against existing control instances and evidence
  requirements.
- Company, organization, process, document, and control-instance validation.

The importers do not read arbitrary server filesystem paths.

## Document Import

Required CSV columns:

```csv
document_code,title,revision,effective_date,owner_login,process_code,document_type,status,attachment_filename,attachment_base64,migration_note,control_instance_code
```

Allowed status values:

- `draft`
- `under_review`
- `approved`
- `active`
- `obsolete`

When an existing active document is imported from an authorized inventory, the
wizard creates the current revision only. It does not invent missing historical
revisions.

## Evidence Import

Required CSV columns:

```csv
evidence_name,control_instance_code,evidence_requirement_name,evidence_type,evidence_date,state,document_code,attachment_filename,attachment_base64,migration_note
```

Allowed state values:

- `draft`
- `submitted`
- `under_review`
- `rejected`

Evidence import intentionally rejects `accepted`. Imported evidence must be
reviewed after migration unless a future controlled validation workflow is
explicitly added.

## Tests

Run:

```bash
./deployment/scripts/odoo-dev.sh test-mission10
```
