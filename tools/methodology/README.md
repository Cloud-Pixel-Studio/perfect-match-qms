# Historical methodology normalizer

This tool converts a historical Perfect Match methodology export into local,
source-derived candidates for later human authoring. It is an ETL/reporting
tool only. It does not import data into Odoo and it does not create Odoo
records.

## Run

```bash
python3 tools/methodology/normalize.py \
  --source /path/to/historical-package.zip \
  --output /path/outside/repository/m25.2-normalized \
  --expected-sha256 <verified-sha256>
```

The output contains an inventory, normalized candidates, taxonomy summary,
tag mappings, review queue, quarantine, manifest, and a short text report.
Output is deterministic for the same source ZIP and tool version. Generated
files must remain in a local ignored workspace and must not be committed.

## Boundaries

The committed part of M25.2 is tooling, schema-by-example, tests, rules,
documentation, and the ADR. The original package and generated
source-derived datasets stay outside tracked production content. Chatter,
users, email addresses, attachments, source IDs, environment metadata, raw AI
prompts, and questionable protected text are excluded or quarantined.

The normalized output is not final Perfect Match customer content. M25.3 or a
later authoring checkpoint must review and author any framework content before
it is versioned as an ISO 9001 content addon.

## Tests

```bash
python3 -m unittest discover -s tools/methodology/tests -p 'test_*.py'
```

The tests use only an original fictional fixture. They do not require the
historical package and do not touch Odoo.
