# PMQMS License Blocked-State Evidence

This document records the safe behavior when an external authority or signed
license is unavailable.

## Expected behavior

- The target environment remains unlicensed.
- No replacement key is generated locally.
- No synthetic `.pmql` is created.
- No license for another UUID is reused.
- Installation stops before seed and customer data initialization.
- The blocking reason is recorded without secrets or full activation payloads.

## Demo2 reference

The Demo2 preparation is blocked when the authority secret and signed license
are unavailable. The target identity and activation request remain outside Git
under the deployment-managed instance directory. Their values must not be
copied into public documentation.

## Acceptance test

The blocked-state test passes when:

1. the official workflow reports the missing-license condition;
2. no `.pmql` is created or imported;
3. no seed or validation command runs;
4. no private-key path is accessed by the target runtime;
5. the target remains isolated and recoverable.

This is a safety result, not a deployment PASS.
